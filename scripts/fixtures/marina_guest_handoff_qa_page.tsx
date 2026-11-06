"use client";
import GuestAiAssistant from "../../components/GuestAiAssistant";
export default function QaGuestHandoff() {
  return <main style={{width:"min(650px,94vw)",margin:"40px auto"}}>
    <GuestAiAssistant token="synthetic-guest-token" locale="ru"
      onSessionExpired={() => { document.body.dataset.expired = "true"; }}
      onHandoffRequested={() => { document.body.dataset.reloaded = "true"; }} />
  </main>;
}
