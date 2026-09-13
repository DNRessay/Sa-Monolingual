FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

COPY aws/functions/process/requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY config.py process.py ./
COPY aws/functions/common.py ./
COPY aws/functions/process/app.py ./

ENV HF_HOME=/tmp/hf
ENV HF_HUB_ENABLE_HF_TRANSFER=0

CMD ["app.handler"]
