FROM python:3.11
WORKDIR / 
COPY . .
RUN pip install -r requirements.txt
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/app/mqtt.py"]
