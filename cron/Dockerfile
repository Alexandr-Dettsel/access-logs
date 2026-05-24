FROM alpine:3.20

RUN apk add --no-cache curl bash coreutils

WORKDIR /cron

COPY collect_logs.sh /cron/collect_logs.sh
RUN chmod +x /cron/collect_logs.sh

COPY crontab /etc/crontabs/root
CMD ["crond", "-f", "-l", "8"]
