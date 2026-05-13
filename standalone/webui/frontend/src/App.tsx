import { RouterProvider } from 'react-router-dom'
import { TickerProvider } from './context/TickerContext'
import { router } from './router'

export default function App() {
  return (
    <TickerProvider>
      <RouterProvider router={router} />
    </TickerProvider>
  )
}
