
def main():
    import sys

    try:
        from packaging import version
    except Exception:
        raise ModuleNotFoundError(
                'Module packaging not found. Try running make setup first.'
                )

    PYTHON_VERSION = "3.12"
    PYTHON_VERSION = version.parse(PYTHON_VERSION)

    minimum = PYTHON_VERSION

    print(f'Parsed minimum Python version is {PYTHON_VERSION}')

    current = sys.version_info
    current_version = version.parse(f'{current.major}.{current.minor}.{current.micro}')

    current_major = current.major
    required_major = minimum.major

    if current_major != required_major:
        raise TypeError(
            f'This project requires Python {required_major}. Found: Python {current.major}'
        )

    else:
        print('>>> Python is in the right ballpark.')

    print(f'current Python version is {current}')
    print(f'required Python version is ^{minimum}')

    # If the current version is lower than required, raise error
    if current_version < minimum:
        raise TypeError(
            f'This project requires Python {minimum}. Found: Python {current}.'
        )
    else:
        print('>>> Environment passed all tests!')


if __name__ == '__main__':
    main()
