import { createBrowserRouter } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import WorkspacePage from './pages/WorkspacePage'
import HistoryPage from './pages/HistoryPage'
import ApiCheckPage from './pages/ApiCheckPage'
import FinetunePage from './pages/FinetunePage'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true, element: <WorkspacePage /> },
      { path: 'finetune', element: <FinetunePage /> },
      { path: 'history', element: <HistoryPage /> },
      { path: 'dev/api-check', element: <ApiCheckPage /> },
    ],
  },
])
