FROM node:20-alpine
WORKDIR /app
# Run as the image's unprivileged `node` user. It owns the tree so `next start`
# can still write .next/cache (image optimisation, revalidatePath).
RUN chown node:node /app
USER node
COPY --chown=node:node package.json package-lock.json ./
RUN npm ci
COPY --chown=node:node . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "start"]
