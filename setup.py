from setuptools import setup, find_packages

setup(
    name="introspec",
    version="1.0.0",
    description="Dual-Agent Introspective Dialogue & Truth Exploration Orchestrator",
    author="Introspec Team",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "introspec": ["web/static/*"],
    },
    entry_points={
        "console_scripts": [
            "introspec=introspec.main:main",
        ],
    },
    python_requires=">=3.8",
)
