FROM docker.io/alpine:latest

LABEL maintainer "OWenT <admin@owent.net>"

COPY bin/v2ray            /usr/local/v2ray/bin/
COPY etc/config.json      /usr/local/v2ray/etc/
COPY share/geo-all.tar.gz /usr/local/v2ray/share/
COPY bin/geoip.dat        /usr/local/v2ray/bin/
COPY bin/geosite.dat      /usr/local/v2ray/bin/
COPY bin/geoip-only-cn-private.dat /usr/local/v2ray/bin/

# sed -i -r 's#dl-cdn.alpinelinux.org#mirrors.tencent.com#g' /etc/apk/repositories ;   \
RUN set -ex ;                                                                          \
  sed -i -r 's#dl-cdn.alpinelinux.org#mirrors.aliyun.com#g' /etc/apk/repositories ;    \
  apk --no-cache add ca-certificates tzdata ;                                          \
  ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime ;                            \
  mkdir -p /var/log/v2ray/ ;                                                           \
  mkdir -p /usr/local/vproxy/bin ; mkdir -p /usr/local/vproxy/etc ; /var/log/vproxy/ ; \
  ln $(find /usr/local/v2ray/bin -type f) /usr/local/vproxy/bin;                       \
  ln $(find /usr/local/v2ray/etc -type f) /usr/local/vproxy/etc;                       \
  ln /usr/local/vproxy/bin/v2ray /usr/local/vproxy/bin/vproxyd;                        \
  chmod +x /usr/local/v2ray/bin/v2ray /usr/local/vproxy/bin/vproxyd;

ENV PATH /usr/local/vproxy/bin/:$PATH

VOLUME /var/log/vproxy

CMD ["vproxyd", "run" "-c", "/usr/local/vproxy/etc/config.json"]

# podman run -d --name vproxy -v /etc/vproxy:/usr/local/vproxy/etc -v /data/logs/vproxy:/var/log/vproxy --cap-add=NET_ADMIN --network=host docker.io/owt5008137/proxy-with-geo vproxy -config=/usr/local/vproxy/etc/config.json
# podman generate systemd vproxy | sudo tee /lib/systemd/system/v2ray.service
# sudo systemctl daemon-reload
