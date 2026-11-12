FROM python:3.15-slim

COPY requirements.txt requirements.txt
RUN pip install -U pip
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

RUN mkdir -p ~/.streamlit && mv config.toml ~/.streamlit/config.toml

ARG GOOGLE_ANALYTICS_ID
RUN if [ -n "$GOOGLE_ANALYTICS_ID" ] ; then \
    python add_ga.py --id $GOOGLE_ANALYTICS_ID ; \
  fi

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "Streamlit_application.py", "--server.address=0.0.0.0", "--server.port=8501"]
