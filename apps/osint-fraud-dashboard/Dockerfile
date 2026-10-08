# Local-development image for the ClearGlass OSINT Fraud Detection prototype.
# One image serves both the one-shot migrate/seed job and the web app.
FROM node:22-alpine
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
RUN chown node:node /app
USER node
COPY --chown=node:node package.json package-lock.json ./
RUN npm ci
COPY --chown=node:node . .
RUN npx prisma generate && npm run build
EXPOSE 3050
# Inside the container the server listens on all interfaces; compose publishes
# it on the host's 127.0.0.1 only.
CMD ["npx", "next", "start", "-H", "0.0.0.0", "-p", "3050"]
