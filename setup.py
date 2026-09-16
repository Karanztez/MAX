from setuptools import setup, find_packages  # type: ignore[import-untyped]
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8") if (this_directory / "README.md").exists() else ""

setup(
    name="max-ai",
    version="1.0.3",
    description="MAX AI Agent — Multi-Provider AI Assistant & Autonomous Tool Runner for GUI & Terminal",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Karanztez",
    license="Non-Commercial / Proprietary",
    url="https://github.com/Karanztez/MAX",
    packages=find_packages(include=["src", "src.*", "max_ai", "max_ai.*"]),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "Pillow>=10.0.0",
        "pystray>=0.19.5; sys_platform == 'win32'",
        "psutil>=5.9.0",
    ],
    extras_require={
        "discord": ["discord.py>=2.3.0"],
        "all": ["discord.py>=2.3.0", "psutil>=5.9.0"],
    },
    entry_points={
        "console_scripts": [
            "max=src.cli:run_cli",
            "max-gui=src.ui.main_window:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
