ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8

# Install requirements for add-on
RUN \
  apk add --no-cache \
    python3 \
    py3-scipy \
    py3-numpy \
    py3-requests

WORKDIR /src

# Copy data for add-on
ADD src /src
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
