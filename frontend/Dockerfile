FROM node:22-alpine AS build

WORKDIR /frontend

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build


# Runtime image
FROM nginx:alpine

# Copy Vite build output to nginx
COPY --from=build /frontend/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]