import { useTranslation } from "react-i18next";
import { Navigate, Route, Routes } from "react-router";

import { useMe } from "./api/queries";
import { DemoBanner, ErrorNote, Loading } from "./components/ui";
import { Admin } from "./screens/Admin";
import { Login, Totp } from "./screens/Login";
import { NewQuote } from "./screens/NewQuote";
import { PositionEditor } from "./screens/position/PositionEditor";
import { QuoteScreen } from "./screens/QuoteScreen";
import { QuotesList } from "./screens/QuotesList";

/** Who is here decides what shows: the login, the admin's code step, or the app. */
export function App() {
  const { t } = useTranslation();
  const me = useMe();
  if (me.isPending) return <Loading />;
  if (me.isError) return <ErrorNote message={t("app.offline")} onRetry={() => void me.refetch()} />;
  if (me.data === null) return <Login />;
  if (!me.data.totp_ok) return <Totp />;
  return (
    <>
      {me.data.is_demo && <DemoBanner />}
      <Routes>
        <Route path="/" element={<QuotesList />} />
        <Route path="/quotes/new" element={<NewQuote />} />
        <Route path="/quotes/:id" element={<QuoteScreen />} />
        <Route path="/quotes/:id/positions/new" element={<PositionEditor />} />
        <Route path="/quotes/:id/positions/:ref" element={<PositionEditor />} />
        <Route path="/admin" element={<Admin />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
