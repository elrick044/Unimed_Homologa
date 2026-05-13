# ESTÁGIO 1: Build do React/Vite
FROM node:20-alpine as build

WORKDIR /app

# Copia os arquivos de dependência e instala
COPY ./cadastro_Unimed/package*.json ./
RUN npm install

# Copia o código fonte e faz o build de produção
COPY ./cadastro_Unimed ./
RUN npm run build

# ESTÁGIO 2: Servidor Nginx
FROM nginx:alpine

# Remove a configuração padrão do Nginx
RUN rm /etc/nginx/conf.d/default.conf

# Copia nossa configuração customizada do Nginx
COPY ./docker/react/nginx.conf /etc/nginx/conf.d

# Copia a pasta dist gerada no Estágio 1 para a pasta pública do Nginx
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

# Inicia o Nginx
CMD ["nginx", "-g", "daemon off;"]