# multi-stage build so that we can keep local build junk out of the runtime
FROM python:3.8-slim as compile-image

RUN apt-get update && apt-get install -y \
    libpq-dev\
    gcc

WORKDIR /build
COPY Pipfile Pipfile.lock ./

# so that the environment goes into the /build/.venv folder
ENV PIPENV_VENV_IN_PROJECT 1

RUN pip install --upgrade pip 
RUN pip install pipenv 
RUN pipenv install --deploy --ignore-pipfile

# the image that will get deployed
FROM python:3.8-slim as runtime-image

# environment
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PATH="/opt/venv/bin:$PATH"

# install other dependencies
RUN apt-get update && apt-get install -y \
    dumb-init\
    postgresql-client

# copy over the environment from the compile-image (to what we set in PATH)
COPY --from=compile-image /build/.venv /opt/venv

# copy the app directory to the image
COPY app/ /app
WORKDIR /app

# Runs "/usr/bin/dumb-init -- /my/script --with --args"
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
