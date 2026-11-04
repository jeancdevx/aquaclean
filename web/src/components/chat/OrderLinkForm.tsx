import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { post } from "@/lib/api";
import type { Case } from "@/lib/event-types";

export function OrderLinkForm({
  caseData,
  onSaved,
  onError,
}: {
  caseData: Case;
  onSaved: () => void;
  onError: (s: string) => void;
}) {
  const [number, setNumber] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <form
      className="notice mt-4"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        try {
          await post(`/cases/${caseData.id}/order-link`, {
            order_number: number,
            expected_version: caseData.version,
          });
          setNumber("");
          onSaved();
        } catch (error) {
          onError((error as Error).message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <label htmlFor="order-number">Vincular pedido verificado</label>
      <Input
        id="order-number"
        placeholder="HIST-DEMO-00001 o DEMO-…"
        value={number}
        onChange={(e) => setNumber(e.target.value)}
      />
      <Button
        variant="outline"
        className="w-full mt-2"
        disabled={busy || number.length < 4}
      >
        Vincular al expediente
      </Button>
      <p className="text-xs mt-2">
        Se valida el cliente y la versión en el backend.
      </p>
    </form>
  );
}
