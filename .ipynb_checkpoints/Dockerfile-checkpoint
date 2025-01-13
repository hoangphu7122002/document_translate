FROM nvidia/cuda:12.3.0-runtime-ubuntu20.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y python3.9 python3.9-dev python3-pip
COPY . /workspace

ADD requirements.txt .
RUN pip install --upgrade wheel setuptools pip
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt
RUN pip install flask-cors

ENV CUDA_DEVICE_ORDER="PCI_BUS_ID"
ENV CUDA_VISIBLE_DEVICES="0"

WORKDIR /workspace

CMD ["python3", "-m", "src.api.api1"]