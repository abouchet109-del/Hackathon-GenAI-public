# Build after running ./setup.sh once (it vendors the Meterless H-MEM reference into vendor/).
FROM node:22-slim
WORKDIR /svc
COPY package.json ./
RUN npm install --omit=dev --silent
COPY server.ts ./
COPY vendor ./vendor
ENV HMEM_HOST=0.0.0.0 HMEM_PORT=8787 HMEM_DIR=/data
EXPOSE 8787
CMD ["npx", "tsx", "server.ts"]
