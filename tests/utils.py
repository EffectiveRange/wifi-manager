import os
import shutil
import time
from difflib import Differ
from pathlib import Path
from typing import Callable, Any

TEST_RESOURCE_ROOT = str(Path(os.path.dirname(__file__)).absolute())
TEST_FILE_SYSTEM_ROOT = str(Path(TEST_RESOURCE_ROOT).joinpath('test_root').absolute())
RESOURCE_ROOT = str(Path(TEST_RESOURCE_ROOT).parent.absolute())


def delete_directory(directory: str) -> None:
    if os.path.isdir(directory):
        shutil.rmtree(directory)


def create_directory(directory: str) -> None:
    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)


def copy_file(source: str, destination: str) -> None:
    create_directory(os.path.dirname(destination))
    shutil.copy(source, destination)


def create_file(file: str, content: str) -> None:
    create_directory(os.path.dirname(file))
    with open(file, 'w') as f:
        f.write(content)


def compare_files(file1: str, file2: str) -> bool:
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        lines1 = f1.readlines()
        lines2 = f2.readlines()

    return compare_lines(lines1, lines2)


def compare_lines(lines1: list[str], lines2: list[str]) -> bool:
    all_lines_match = True

    for line in Differ().compare(lines1, lines2):
        if not line.startswith('?'):
            print(line.strip('\n'))
        if line.startswith(('-', '+', '?')):
            all_lines_match = False

    return all_lines_match


def wait_for_condition(timeout: float, condition: Callable[..., bool], *args: Any, **kwargs: Any) -> None:
    time_step = 0.01
    total_time = 0.0

    while total_time <= timeout:
        if args or kwargs:
            if condition(*args, **kwargs):
                return
        else:
            if condition():
                return
        total_time += time_step
        time.sleep(time_step)
    else:
        raise TimeoutError(f'Failed to meet condition in {timeout} seconds')


def wait_for_assertion(timeout: float, assertion: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    time_step = 0.01
    total_time = 0.0
    error_message = ''

    while total_time <= timeout:
        try:
            if args or kwargs:
                assertion(*args, **kwargs)
            else:
                assertion()
                print(total_time)
            return
        except AssertionError as error:
            error_message = str(error)
            total_time += time_step
            time.sleep(time_step)
    else:
        raise AssertionError(f'Failed to assert in {timeout} seconds: {error_message}')
