FROM python:3.8.10

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y python3 && \
    apt-get install -y python3-pip

RUN mkdir /app
WORKDIR /app

RUN pip3 install Flask==3.0.2
RUN pip3 install pytest==8.0.0


COPY app.py /app/app.py
COPY iss_tracker.py /app/iss_tracker.py
COPY test_iss_tracker.py /app/test_iss_tracker.py

ENTRYPOINT ["python"]
CMD ["app.py"]
