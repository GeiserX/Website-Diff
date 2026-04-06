"""Setup configuration for Wayback-Diff."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="wayback-diff",
    version="1.1.0",
    author="geiserx",
    author_email="sergio@geiser.cloud",
    description="A comprehensive tool for comparing web pages with Wayback Machine support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/GeiserX/Wayback-Diff",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Topic :: Internet :: WWW/HTTP",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
    ],
    extras_require={
        "visual": [
            "selenium>=4.15.0",
            "Pillow>=10.0.0",
            "webdriver-manager>=4.0.0",
            "numpy>=1.24.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "wayback-diff=wayback_diff.cli:main",
        ],
    },
)
