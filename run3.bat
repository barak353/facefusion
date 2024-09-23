@echo off
SETLOCAL EnableDelayedExpansion

REM Set the starting index
SET index=105855
REM Set the ending index (adjust as needed)
SET end_index=200000

:loop
REM Construct the new target_path and new_output_path
SET new_target_path=C:\Users\User\Documents\GitHub\content\vid!index!.mp4
SET new_output_path=C:\Users\User\Documents\GitHub\content\out\vid!index!m_out.mp4

REM Update the facefusion.ini file
(
    FOR /F "usebackq delims=" %%a IN ("facefusion.ini") DO (
        SET line=%%a
        ECHO !line! | FINDSTR /B /C:"target_path =" >nul
        IF NOT ERRORLEVEL 1 (
            ECHO target_path =!new_target_path!
        ) ELSE (
            ECHO !line! | FINDSTR /B /C:"output_path =" >nul
            IF NOT ERRORLEVEL 1 (
                ECHO output_path =!new_output_path!
            ) ELSE (
                ECHO !line!
            )
        )
    )
) > facefusion_new.ini

MOVE /Y facefusion_new.ini facefusion.ini

REM Run the command
python facefusion.py headless-run

REM Increment the index
SET /A index=!index!+1

REM Check if the index is less than or equal to end_index
IF !index! LEQ !end_index! (
    GOTO loop
)

ENDLOCAL
