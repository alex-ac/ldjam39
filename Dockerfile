FROM alpine:latest
ADD . /app
RUN apk add --no-cache python2 py-pip && pip install -r /app/requirements.txt
CMD [ "/app/bot.py" ]
