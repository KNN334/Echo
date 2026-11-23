import React, { lazy, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout.jsx'
import { EmptyState } from './components/UI.jsx'
import Overview from './pages/Overview.jsx'
import './styles/global.css'

const About = lazy(() => import('./pages/About.jsx'))
const Features = lazy(() => import('./pages/Features.jsx'))
const Results = lazy(() => import('./pages/Results.jsx'))
const Patients = lazy(() => import('./pages/Patients.jsx'))
const PatientDetail = lazy(() => import('./pages/PatientDetail.jsx'))

createRoot(document.getElementById('root')).render(
  <HashRouter>
    <Layout>
      <Suspense fallback={<EmptyState title="正在加载页面…" loading />}>
        <Routes>
          <Route index element={<Overview />} />
          <Route path="/about" element={<About />} />
          <Route path="/features" element={<Features />} />
          <Route path="/results" element={<Results />} />
          <Route path="/patients" element={<Patients />} />
          <Route path="/patients/:id" element={<PatientDetail />} />
          <Route path="*" element={<EmptyState title="页面不存在" to="/" action="返回概览" />} />
        </Routes>
      </Suspense>
    </Layout>
  </HashRouter>,
)
