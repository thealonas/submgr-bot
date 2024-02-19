FROM python:alpine
WORKDIR /app
COPY . .
RUN apk --no-cache add gcc libc-dev libffi-dev
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
