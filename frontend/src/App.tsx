import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, Route, Routes } from "react-router";

import { useMe } from "./api/queries";
import { DemoBanner, ErrorNote, Loading } from "./components/ui";
import { followWorkshopLanguage } from "./i18n";
import { setCurrency } from "./lib/format";
import { Join } from "./screens/Join";
import { Landing } from "./screens/Landing";
import { Login, Totp } from "./screens/Login";
import { NewQuote } from "./screens/NewQuote";
import { PositionEditor } from "./screens/position/PositionEditor";
import { QuoteScreen } from "./screens/QuoteScreen";
import { QuotesList } from "./screens/QuotesList";
import { Account } from "./screens/workshop/Account";
import { Details } from "./screens/workshop/Details";
import { Hub } from "./screens/workshop/Hub";
import { PriceListEditor } from "./screens/workshop/PriceListEditor";
import { Prices } from "./screens/workshop/Prices";
import { Setup } from "./screens/workshop/Setup";
import { SheetEditor } from "./screens/workshop/SheetEditor";
import { Systems } from "./screens/workshop/Systems";
import { Team } from "./screens/workshop/Team";

/** Who is here decides what shows: the front door, the two-step code, or the workshop's app. */
export function App() {
  const { t } = useTranslation();
  const me = useMe();
  const language = me.data?.language;
  useEffect(() => {
    if (language) followWorkshopLanguage(language);
  }, [language]);

  if (me.isPending) return <Loading />;
  if (me.isError) return <ErrorNote message={t("app.offline")} onRetry={() => void me.refetch()} />;
  if (me.data === null) {
    return (
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/join" element={<Join />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    );
  }
  if (!me.data.totp_ok) return <Totp />;
  // Every amount on every screen is in the workshop's currency.
  setCurrency(me.data.currency);
  return (
    <>
      {me.data.is_demo && <DemoBanner expiresAt={me.data.sandbox_expires_at} />}
      <Routes>
        <Route path="/" element={<QuotesList />} />
        <Route path="/quotes/new" element={<NewQuote />} />
        <Route path="/quotes/:id" element={<QuoteScreen />} />
        <Route path="/quotes/:id/positions/new" element={<PositionEditor />} />
        <Route path="/quotes/:id/positions/:ref" element={<PositionEditor />} />
        <Route path="/workshop" element={<Hub />} />
        <Route path="/workshop/setup" element={<Setup />} />
        <Route path="/workshop/systems" element={<Systems />} />
        <Route path="/workshop/systems/:id" element={<SheetEditor />} />
        <Route path="/workshop/prices" element={<Prices />} />
        <Route path="/workshop/prices/:id" element={<PriceListEditor />} />
        <Route path="/workshop/team" element={<Team />} />
        <Route path="/workshop/details" element={<Details />} />
        <Route path="/workshop/account" element={<Account />} />
        <Route path="/admin" element={<Navigate to="/workshop" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
