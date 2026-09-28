import { Outlet } from 'react-router-dom';
import TopNavbar from '../components/common/TopNavbar';

export default function MainLayout() {
  return (
    <div className="min-h-screen bg-page">
      <TopNavbar />
      <main className="mx-auto w-full max-w-[1600px] px-4 py-6 sm:px-7 sm:py-8">
        <Outlet />
      </main>
    </div>
  );
}
