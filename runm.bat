@echo off
setlocal enabledelayedexpansion

rem Set the path to your Python interpreter
set python_exe=python

rem Loop through files named "vid1", "vid2", etc.
for /L %%i in (975,1,20000) do (
    set "file=C:\Users\User\Documents\GitHub\content\vid%%i.mp4"
    set "file_out=C:\Users\User\Documents\GitHub\content\out\vid%%im_out.mp4"
    set "file_img=C:\Users\User\Documents\GitHub\content\img.jpg"
	
    rem Check if the file exists
    if exist !file! (
        echo Processing !file!
        
		rem Build the command and store it in a variable
		set "command=!python_exe! run.py -s !file_img! -t !file! -o !file_out! --frame-processor face_swapper face_enhancer --face-swapper-model inswapper_128 --face-enhancer-model gpen_bfr_512 --temp-frame-format bmp --output-video-quality 48 --output-video-encoder hevc_nvenc --execution-providers cuda --execution-thread-count 128 --execution-queue-count 4 --headless --face-selector-mode many  --face-mask-padding 0 0 33 0 --skip-download --video-memory-strategy tolerant --output-video-preset ultrafast"
        
		rem Print the command
        echo command: !command!
        
        rem Execute the command
        !command!
    ) else (
        echo File !file! not found. Moving to the next file.
    )
)

endlocal