# ML Security CLI - container image
# Build:  docker build -t ml-security-cli .
# Run:    docker run --rm ml-security-cli --report

FROM python:3.12-slim

WORKDIR /app

# CPU-only PyTorch keeps the image small (no GPU libraries)
RUN pip install --no-cache-dir torch torchvision \
        --index-url https://download.pytorch.org/whl/cpu

# The CLI evaluates the model on the MNIST test set, so download it at build time
RUN python -c "import torchvision; torchvision.datasets.MNIST(root='data', train=False, download=True)"

# The tool and the trained baseline model it evaluates
COPY ml_security_cli.py .
COPY models/mnist_cnn_baseline.pth models/mnist_cnn_baseline.pth

RUN mkdir -p results

ENTRYPOINT ["python", "ml_security_cli.py"]
CMD ["--report"]
