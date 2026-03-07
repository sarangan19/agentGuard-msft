from setuptools import find_packages, setup


def _read_requirements(path):
    lines = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            lines.append(line)
    return lines


setup(
    name="agentguard",
    version="4.2.14",
    description="AgentGuard terminal middleware and dashboard integration",
    packages=find_packages(),
    install_requires=_read_requirements("requirements.txt"),
    python_requires=">=3.10",
)
