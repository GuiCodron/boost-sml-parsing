FROM ubuntu:18.04

MAINTAINER Guilhem Codron <guilhem.codron@gmail.com>


RUN apt-get update
RUN apt install -y apt-utils \
  llvm-8 \
  clang-8 \
  python3.6 \
  python3-pip
RUN pip3 install clang \
  toposort


ENV CLANG_LIBRARY_PATH=/usr/lib/llvm-8.0/lib
COPY sml-parsing /sml-parsing

ENTRYPOINT bash
WORKDIR /sml-parsing