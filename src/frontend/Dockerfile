FROM node:14.16.0-slim AS builder
RUN npm install -g react-scripts --silent

COPY . .

RUN yarn install
RUN yarn run build

FROM nginx:stable

COPY --from=builder /build /usr/share/nginx/html
COPY nginx.default.conf /etc/nginx/conf.d/default.conf

COPY req.conf /

RUN mkdir -p /certs
COPY ssl.crt /certs
COPY ssl.key /certs

RUN chown -R nginx:nginx /usr/share/nginx/html && chmod -R 755 /usr/share/nginx/html && \
        chown -R nginx:nginx /certs && \
        chown -R nginx:nginx /var/cache/nginx && \
        chown -R nginx:nginx /var/log/nginx && \
        chown -R nginx:nginx /etc/nginx/conf.d
RUN touch /var/run/nginx.pid && \
        chown -R nginx:nginx /var/run/nginx.pid

USER nginx