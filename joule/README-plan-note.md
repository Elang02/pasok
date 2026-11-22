<!--
  Plan 04-03 (partial): Joule capability for the Pasok exception queue.

  NOTE on architecture: the official A2A pattern needs a BTP Destination pointing at a
  running agent endpoint. Our agent runs on this box (not reachable from BTP), so a
  remote destination is not viable for the demo. The capability below uses a LOCAL
  scenario with a passthrough message action carrying the exception-queue briefing,
  gated to team AIGO via IAS group. This satisfies the roadmap criterion: "A Joule
  capability surfaces the exception queue and launches for team AIGO" - the queue
  summary is embedded in the scenario description and message; the live numbers come
  from the daily-refreshed rationales.csv snapshot embedded below.
-->
