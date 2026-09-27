export type BloodStatus = "AVAILABLE" | "LIMITED" | "EMPTY" | "UNKNOWN";
export type BloodType = "A" | "B" | "AB" | "O";
export type Rhesus = "+" | "-";

export type BloodInventory = {
  blood_type: BloodType;
  rhesus: Rhesus;
  status: BloodStatus;
  units: number | null;
  quantity?: number | null;
};

export type BloodFacility = {
  id: string;
  name: string;
  facility_type?: string;
  city: string;
  address: string;
  location?: string;
  verified: boolean;
  last_updated: string;
  data_source: string;
  demo_data: boolean;
  data_mode?: "SIMULATED" | "LIVE";
  refresh_hint_seconds?: number;
  inventory: BloodInventory[];
};

export const STATUS_VARIANT: Record<BloodStatus, "success" | "warning" | "error" | "neutral"> = {
  AVAILABLE: "success",
  LIMITED: "warning",
  EMPTY: "error",
  UNKNOWN: "neutral",
};

export const BLOOD_TYPES: BloodType[] = ["A", "B", "AB", "O"];
export const RHESUS_VALUES: Rhesus[] = ["+", "-"];

export function facilityDataMode(facility: BloodFacility): "SIMULATED" | "LIVE" {
  return facility.data_mode ?? (facility.demo_data ? "SIMULATED" : "LIVE");
}
