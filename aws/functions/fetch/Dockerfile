FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

COPY aws/functions/fetch/requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY config.py fetch.py ./
COPY aws/functions/common.py ./
COPY aws/functions/fetch/app.py ./

ENV HF_HOME=/tmp/hf
ENV HF_HUB_ENABLE_HF_TRANSFER=0

CMD ["app.handler"]
