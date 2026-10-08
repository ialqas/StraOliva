"use client";

import { Card, CardTitle } from "@/components/Card";
import { InfoTooltip } from "@/components/InfoTooltip";
import type { Greetings } from "@/lib/api";
import { useLang } from "@/lib/i18n";

interface Props {
  data: Greetings | undefined;
}

function formatShortDate(iso: string, locale: string): string {
  return new Date(iso).toLocaleDateString(locale, { day: "2-digit", month: "short" });
}

export function GreetingsCard({ data }: Props) {
  const { t, locale } = useLang();

  if (!data) {
    return <Card className="animate-pulse h-40">&nbsp;</Card>;
  }

  return (
    <Card className="flex flex-col gap-3">
      <CardTitle>
        <InfoTooltip
          text={t(
            "Summe aller Zahlen, die du als Aktivitäts-Beschreibung hinterlegt hast. Nur Beschreibungen, die ausschließlich aus einer Zahl bestehen, werden gezählt.",
            "Sum of all numbers you entered as activity descriptions. Only descriptions consisting solely of a number are counted.",
          )}
        >
          {t("Zurückgegrüßt", "Greeted back")}
        </InfoTooltip>
      </CardTitle>

      {data.activities > 0 ? (
        <>
          <div>
            <span className="text-[30px] font-medium tabular-nums">{data.total}</span>
            <span className="text-base text-gray-400 dark:text-gray-500 ml-1">
              {data.total === 1 ? t("Person", "person") : t("Personen", "people")}
            </span>
          </div>
          <p className="text-[13px] text-gray-500 dark:text-gray-400 leading-snug">
            Ø {data.avg_per_activity} {t("pro Aktivität", "per activity")} · {data.activities}{" "}
            {data.activities === 1
              ? t("Aktivität mit Zahl", "activity with a number")
              : t("Aktivitäten mit Zahl", "activities with a number")}
          </p>
          {data.best && (
            <p className="text-[13px] text-gray-400 dark:text-gray-500 leading-snug">
              {t("Bestwert", "Best")} {data.best.count} {t("am", "on")} {formatShortDate(data.best.start_time, locale)}
            </p>
          )}
        </>
      ) : (
        <>
          <div className="text-[30px] font-medium text-gray-300 dark:text-gray-600">—</div>
          <p className="text-[13px] text-gray-500 dark:text-gray-400 leading-snug">
            {t(
              "Noch keine Aktivität, deren Beschreibung nur aus einer Zahl besteht. Beschreibungen werden beim Sync von Strava geholt.",
              "No activity yet whose description is just a number. Descriptions are fetched from Strava during sync.",
            )}
          </p>
        </>
      )}
    </Card>
  );
}
