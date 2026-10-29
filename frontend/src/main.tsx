import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './studio.css'
import App from './Studio.tsx'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
const client=new QueryClient({defaultOptions:{queries:{retry:false,staleTime:1000}}})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={client}><App /></QueryClientProvider>
  </StrictMode>,
)
