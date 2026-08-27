# Builder image follows the one upstream sing-box validated for each release
# (passed by CI via --build-arg GO_IMAGE=...); golang:1.25-alpine is only the fallback.
# Never use floating tags here: golang:alpine/1-alpine currently track Go 1.27,
# whose encoding/json/v2 dropped APIs required by go-json-experiment/json pinned by v1.13.x.
ARG GO_IMAGE=golang:1.25-alpine
FROM --platform=$BUILDPLATFORM ${GO_IMAGE} AS builder

LABEL maintainer="nekohasekai <contact-git@sekai.icu>"
COPY . /go/src/github.com/sagernet/sing-box
WORKDIR /go/src/github.com/sagernet/sing-box
ARG TARGETOS TARGETARCH
ARG GOPROXY=""
ENV GOPROXY ${GOPROXY}
ENV CGO_ENABLED=0
ENV GOOS=$TARGETOS
ENV GOARCH=$TARGETARCH
RUN apk add git build-base
RUN set -ex \
  && export COMMIT=$(git rev-parse --short HEAD) \
  && export VERSION=$(go run ./cmd/internal/read_tag) \
  && go build -v -trimpath -tags \
  "with_gvisor,with_quic,with_dhcp,with_wireguard,with_utls,with_acme,with_clash_api,with_tailscale" \
  -o /go/bin/vbox \
  -ldflags "-X \"github.com/sagernet/sing-box/constant.Version=$VERSION\" -s -w -buildid=" \
  ./cmd/sing-box
FROM --platform=$TARGETPLATFORM alpine AS dist
LABEL maintainer="nekohasekai <contact-git@sekai.icu>"
RUN set -ex \
  && apk upgrade \
  && apk add bash tzdata ca-certificates \
  && rm -rf /var/cache/apk/*
COPY --from=builder /go/bin/vbox /usr/local/bin/vbox
COPY data/share/sing-geosite /usr/share/vbox/geosite
COPY data/share/sing-geoip /usr/share/vbox/geoip
COPY data/share/geoip.db data/share/geoip-cn.db data/share/geosite.db data/share/geosite-cn.db /usr/share/vbox/
ENTRYPOINT ["vbox"]
