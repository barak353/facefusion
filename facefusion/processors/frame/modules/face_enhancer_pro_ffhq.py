from typing import Any, List, Callable
import cv2
import threading
import numpy
import onnxruntime

import facefusion.globals
from facefusion import wording
from facefusion.core import update_status
from facefusion.face_analyser import get_many_faces
from facefusion.typing import Frame, Face, ProcessMode
from facefusion.utilities import conditional_download, resolve_relative_path, is_image, is_video
from facefusion.vision import read_image, read_static_image, write_image

FRAME_PROCESSOR = None
THREAD_SEMAPHORE : threading.Semaphore = threading.Semaphore()
THREAD_LOCK : threading.Lock = threading.Lock()
NAME = 'FACEFUSION.FRAME_PROCESSOR.FACE_ENHANCER_PRO_FFHQ'


def get_frame_processor() -> Any:
	global FRAME_PROCESSOR

	with THREAD_LOCK:
		if FRAME_PROCESSOR is None:
			model_path = resolve_relative_path('../.assets/models/GFPGANv1.4.onnx')
			FRAME_PROCESSOR = onnxruntime.InferenceSession(model_path, providers = facefusion.globals.execution_providers)
	return FRAME_PROCESSOR


def clear_frame_processor() -> None:
	global FRAME_PROCESSOR

	FRAME_PROCESSOR = None


def pre_check() -> bool:
	download_directory_path = resolve_relative_path('../.assets/models')
	conditional_download(download_directory_path, [ 'https://github.com/facefusion/facefusion-assets/releases/download/models/GFPGANv1.4.onnx' ])
	return True


def pre_process(mode : ProcessMode) -> bool:
	if mode in [ 'output', 'preview' ] and not is_image(facefusion.globals.target_path) and not is_video(facefusion.globals.target_path):
		update_status(wording.get('select_image_or_video_target') + wording.get('exclamation_mark'), NAME)
		return False
	if mode == 'output' and not facefusion.globals.output_path:
		update_status(wording.get('select_file_or_directory_output') + wording.get('exclamation_mark'), NAME)
		return False
	return True


def post_process() -> None:
	clear_frame_processor()


def ffhq_align_crop(img, landmark):
	ffhq_template = numpy.array([
		[192.98138, 239.94708], [318.90277, 240.1936],
		[256.63416, 314.01935], [201.26117, 371.41043],
		[313.08905, 371.15118]
	], dtype=numpy.float32)
	affine_matrix = cv2.estimateAffinePartial2D(landmark, ffhq_template, method=cv2.LMEDS)[0]
	cropped_face = cv2.warpAffine(img, affine_matrix, (512, 512), borderMode=cv2.BORDER_CONSTANT, borderValue=(135, 133, 132))
	return cropped_face, affine_matrix


def enhance_face(target_face: Face, temp_frame: Frame) -> Frame:
	face_enhancer = get_frame_processor()
	temp_face, matrix = ffhq_align_crop(temp_frame, target_face['kps'])
	temp_face = temp_face.astype(numpy.float32)[:,:,::-1] / 255.0
	temp_face = (temp_face - 0.5) / 0.5
	temp_face = numpy.expand_dims(temp_face.transpose(2, 0, 1), axis = 0).astype(numpy.float32)

	with THREAD_SEMAPHORE:
		temp_face = face_enhancer.run(None, {face_enhancer.get_inputs()[0].name: temp_face})[0][0]

	temp_face = numpy.clip(temp_face, -1, 1)
	temp_face = (temp_face + 1) / 2
	temp_face = temp_face.transpose(1, 2, 0)
	temp_face = (temp_face * 255.0).round()
	temp_face = temp_face.astype(numpy.uint8)[:,:,::-1]

	inverse_affine = cv2.invertAffineTransform(matrix)
	h, w = temp_frame.shape[0:2]
	face_h, face_w = temp_face.shape[0:2]
	inv_restored = cv2.warpAffine(temp_face, inverse_affine, (w, h))
	mask = numpy.ones((face_h, face_w, 3), dtype = numpy.float32)
	inv_mask = cv2.warpAffine(mask, inverse_affine, (w, h))
	inv_mask_erosion = cv2.erode(inv_mask, numpy.ones((2, 2), numpy.uint8))
	inv_restored_remove_border = inv_mask_erosion * inv_restored
	total_face_area = numpy.sum(inv_mask_erosion) // 3
	w_edge = int(total_face_area ** 0.5) // 20
	erosion_radius = w_edge * 2
	inv_mask_center = cv2.erode(inv_mask_erosion, numpy.ones((erosion_radius, erosion_radius), numpy.uint8))
	blur_size = w_edge * 2
	inv_soft_mask = cv2.GaussianBlur(inv_mask_center, (blur_size + 1, blur_size + 1), 0)
	temp_frame = inv_soft_mask * inv_restored_remove_border + (1 - inv_soft_mask) * temp_frame
	temp_frame = temp_frame.clip(0, 255).astype('uint8')
	return temp_frame


def process_frame(source_face : Face, reference_face : Face, temp_frame : Frame) -> Frame:
	many_faces = get_many_faces(temp_frame)
	if many_faces:
		for target_face in many_faces:
			temp_frame = enhance_face(target_face, temp_frame)
	return temp_frame


def process_frames(source_path : str, temp_frame_paths : List[str], update_progress: Callable[[], None]) -> None:
	for temp_frame_path in temp_frame_paths:
		temp_frame = read_image(temp_frame_path)
		result_frame = process_frame(None, None, temp_frame)
		write_image(temp_frame_path, result_frame)
		update_progress()


def process_image(source_path : str, target_path : str, output_path : str) -> None:
	target_frame = read_static_image(target_path)
	result_frame = process_frame(None, None, target_frame)
	write_image(output_path, result_frame)


def process_video(source_path : str, temp_frame_paths : List[str]) -> None:
	facefusion.processors.frame.core.multi_process_frames(None, temp_frame_paths, process_frames)
