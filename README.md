* Inicialmente desenvolveremos o projeto para suporte ao tailwind com prompt

```
npm create vite@latest cadastro_Unimed -- --template react
```

* copiar cada passo do site para a instalação do tailwind dentro do diretório correto , no caso cadastro_Unimed

```
npm install tailwindcss @tailwindcss/vite
```

* Em vite.config.js alterar para o seguinte formato 

```
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(), 
  ],
})

```


* Em index.css fazer o import 

```
@import "tailwindcss";

```

* Por ultimo o comando 

```
npm run dev 
```

* Para rodar a API 

```
uvicorn main:app --reload --port 3000
```

* Para estrutura multipaginas colocaremos dentro do diretório src um subdiretorio chamado pages, assim como o diretrório components.

* Colocaremos um roteador para caminhar entre as paginas dentro de app.jsx
* Vamos criar um layout