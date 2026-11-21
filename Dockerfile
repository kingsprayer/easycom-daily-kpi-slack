FROM node:22-alpine

WORKDIR /app

# Set production environment and default port
ENV NODE_ENV=production \
    PORT=5000

# Install dependencies first for efficient layer caching
COPY package.json package-lock.json* ./
RUN npm install --omit=dev

# Copy application source code
COPY . .

# Expose web dashboard port
EXPOSE 5000

# Start Express dashboard server
CMD ["node", "web_app.js"]
