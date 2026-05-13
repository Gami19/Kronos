import { NavLink, Outlet } from 'react-router-dom'

export default function MainLayout() {
  return (
    <div className="layout">
      <header className="layout__header">
        <h1>Kronos Web UI</h1>
        <p>React ワークスペース</p>
      </header>
      <nav className="layout__nav">
        <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>
          ワークスペース
        </NavLink>
        <NavLink to="/finetune" className={({ isActive }) => (isActive ? 'active' : '')}>
          ファインチューン
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => (isActive ? 'active' : '')}>
          過去結果
        </NavLink>
        <NavLink to="/dev/api-check" className={({ isActive }) => (isActive ? 'active' : '')}>
          API 確認
        </NavLink>
      </nav>
      <main className="layout__main">
        <Outlet />
      </main>
    </div>
  )
}
