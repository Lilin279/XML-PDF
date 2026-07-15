"""Setup for jats2pdf - JATS XML to PDF converter."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="jats2pdf",
    version="1.0.0",
    description="Convert JATS XML academic articles to publication-ready PDF",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="JATS2PDF Team",
    url="https://github.com/kkdj28/jats2pdf-engine",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "jats2pdf": ["templates/**/*", "templates/css/*"],
    },
    install_requires=[
        "lxml>=5.0.0",
        "weasyprint>=60.0",
        "xhtml2pdf>=0.2.0",
        "Jinja2>=3.1.0",
        "click>=8.1.0",
        "cssselect2>=0.7.0",
        "playwright>=1.40.0",
        "PyPDF2>=3.0.0",
        "reportlab>=4.0.0",
    ],
    entry_points={
        "console_scripts": [
            "jats2pdf=jats2pdf.cli:main",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Text Processing :: Markup :: XML",
        "Topic :: Scientific/Engineering",
    ],
)
