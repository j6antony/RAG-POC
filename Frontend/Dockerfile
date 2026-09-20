From node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

EXPOSE 5173

#run npm dev and then pass the host port to vite
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

