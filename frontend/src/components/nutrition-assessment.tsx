"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Check, HeartPulse, Loader2, ShieldCheck } from "lucide-react";
import { Alert, Button, Input, Select, Textarea } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import {
  nutritionResultPath,
  ELDERLY_CONDITION_OPTIONS,
  elderlyConditionLabel,
  saveNutritionResult,
  type ElderlyCondition,
  type NutritionAssessmentPayload,
  type NutritionFoodGroup,
  type NutritionResult,
  type NutritionStage,
  type NutritionValidation,
} from "@/lib/nutrition";

const CHILD_STEPS = ["Basic Information", "Eating Context", "Dietary Information", "Review"];
const ELDERLY_STEPS = ["Informasi Dasar", "Kebiasaan Makan Lansia", "Kondisi Kesehatan", "Preferensi & Pantangan", "Review"];
const appetiteOptions = [
  { label: "Nafsu makan biasa", value: "typical" },
  { label: "Cenderung rendah", value: "low" },
  { label: "Cenderung tinggi", value: "high" },
];
const FOOD_GROUP_OPTIONS: Array<{ value: NutritionFoodGroup; label: string }> = [
  { value: "grains", label: "Serealia / umbi" },
  { value: "legumes", label: "Kacang-kacangan" },
  { value: "dairy", label: "Susu / olahannya" },
  { value: "animal_source", label: "Daging / ikan / unggas" },
  { value: "eggs", label: "Telur" },
  { value: "vitamin_a_produce", label: "Sayur/buah kaya vitamin A" },
  { value: "other_produce", label: "Sayur/buah lainnya" },
  { value: "breastmilk", label: "ASI" },
];

function listFromText(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean).slice(0, 10);
}

function validationVariant(status?: NutritionValidation["status"]) {
  if (status === "INVALID") return "error" as const;
  if (status === "WARNING") return "warning" as const;
  return "success" as const;
}

function localDateString() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function calculateAgeMonths(dateOfBirth: string, assessmentDate: string) {
  if (!dateOfBirth || !assessmentDate) return null;
  const [birthYear, birthMonth, birthDay] = dateOfBirth.split("-").map(Number);
  const [year, month, day] = assessmentDate.split("-").map(Number);
  if (![birthYear, birthMonth, birthDay, year, month, day].every(Number.isFinite)) return null;
  let months = (year - birthYear) * 12 + month - birthMonth;
  if (day < birthDay) months -= 1;
  return months >= 0 ? months : null;
}

function childBand(stage: NutritionStage, ageMonths: number | null) {
  if (ageMonths === null) return "Belum dihitung";
  if (stage === "mpasi") {
    if (ageMonths <= 8) return "6–8 bulan";
    if (ageMonths <= 11) return "9–11 bulan";
    return "12–23 bulan";
  }
  if (stage === "toddler") return "24–59 bulan";
  return "";
}

export function NutritionAssessment({ stage }: { stage: NutritionStage }) {
  const router = useRouter();
  const steps = stage === "elderly" ? ELDERLY_STEPS : CHILD_STEPS;
  const finalStep = steps.length - 1;
  const [step, setStep] = useState(0);
  const [assessmentDate] = useState(localDateString);
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [age, setAge] = useState(stage === "elderly" ? "65" : "");
  const [sex, setSex] = useState<"" | "female" | "male">("");
  const [weight, setWeight] = useState("");
  const [height, setHeight] = useState("");

  const [feedingMode, setFeedingMode] = useState("");
  const [mpasiHistory, setMpasiHistory] = useState<"not_started" | "started">("started");
  const [textureLevel, setTextureLevel] = useState("smooth_mashed");
  const [appetite, setAppetite] = useState<"low" | "typical" | "high">("typical");
  const [mealFrequency, setMealFrequency] = useState(stage === "mpasi" ? "2" : "3");
  const [snackFrequency, setSnackFrequency] = useState("1");
  const [mealRoutine, setMealRoutine] = useState<"regular" | "mixed" | "irregular">("mixed");
  const [animalSourceFoodDays, setAnimalSourceFoodDays] = useState("0");
  const [fruitVegetableDays, setFruitVegetableDays] = useState("0");
  const [recentFoodGroups, setRecentFoodGroups] = useState<NutritionFoodGroup[]>([]);

  const [responsiveFeeding, setResponsiveFeeding] = useState<"usually" | "sometimes" | "rarely">("sometimes");
  const [feedingMethod, setFeedingMethod] = useState<"caregiver_assisted" | "mixed" | "self_feeding">("mixed");
  const [foodRejection, setFoodRejection] = useState<"none" | "occasional" | "frequent">("none");
  const [foodRejectionDetails, setFoodRejectionDetails] = useState("");
  const [feedingDifficulty, setFeedingDifficulty] = useState<"none" | "some" | "significant">("none");
  const [feedingDifficultyDetails, setFeedingDifficultyDetails] = useState("");
  const [textureRefusal, setTextureRefusal] = useState(false);
  const [pressureToEat, setPressureToEat] = useState(false);
  const [screenDuringMeals, setScreenDuringMeals] = useState(false);
  const [selfFeedingOpportunity, setSelfFeedingOpportunity] = useState(false);
  const [mealEnvironment, setMealEnvironment] = useState<"calm" | "mixed" | "distracted">("mixed");
  const [mealtimeDuration, setMealtimeDuration] = useState("30");
  const [foodPreferences, setFoodPreferences] = useState("");
  const [sweetenedBeverageExposure, setSweetenedBeverageExposure] = useState(false);
  const [sweetBeverageDays, setSweetBeverageDays] = useState("0");
  const [repeatedExposureDays, setRepeatedExposureDays] = useState("0");
  const [waterPrimaryBeverage, setWaterPrimaryBeverage] = useState(true);
  const [safetyHygieneOk, setSafetyHygieneOk] = useState(true);
  const [barriers, setBarriers] = useState("");

  const [activityLevel, setActivityLevel] = useState<"low" | "moderate" | "high">("moderate");
  const [hydrationPattern, setHydrationPattern] = useState<"regular" | "sometimes_low" | "often_low" | "unknown">("unknown");
  const [eatingIndependence, setEatingIndependence] = useState<"independent" | "needs_reminder" | "needs_setup" | "needs_assistance" | "unknown">("unknown");
  const [caregiverSupport, setCaregiverSupport] = useState<"none" | "sometimes" | "daily" | "unknown">("unknown");
  const [chewingDifficulty, setChewingDifficulty] = useState<boolean | null>(stage === "elderly" ? null : false);
  const [swallowingDifficulty, setSwallowingDifficulty] = useState<boolean | null>(stage === "elderly" ? null : false);
  const [allergies, setAllergies] = useState("");
  const [restrictions, setRestrictions] = useState("");
  const [medicalContext, setMedicalContext] = useState("");
  const [hasCondition, setHasCondition] = useState<boolean | null>(stage === "elderly" ? null : false);
  const [conditions, setConditions] = useState<ElderlyCondition[]>([]);
  const [otherCondition, setOtherCondition] = useState("");
  const [elderlyDraftLoaded, setElderlyDraftLoaded] = useState(stage !== "elderly");
  const [notes, setNotes] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [validationAttempted, setValidationAttempted] = useState(false);
  const [validation, setValidation] = useState<NutritionValidation | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationError, setValidationError] = useState("");

  useEffect(() => {
    if (stage !== "elderly" || typeof window === "undefined") return;
    try {
      const raw = sessionStorage.getItem("sehatin:nutrition-assessment-draft:elderly");
      if (raw) {
        const draft = JSON.parse(raw) as { has_condition?: boolean | null; conditions?: ElderlyCondition[]; other_condition?: string; hydration_pattern?: typeof hydrationPattern; eating_independence?: typeof eatingIndependence; caregiver_support?: typeof caregiverSupport };
        if (typeof draft.has_condition === "boolean") setHasCondition(draft.has_condition);
        if (Array.isArray(draft.conditions)) setConditions(draft.conditions.filter((item): item is ElderlyCondition => ELDERLY_CONDITION_OPTIONS.some((option) => option.value === item)));
        if (typeof draft.other_condition === "string") setOtherCondition(draft.other_condition);
        if (["regular","sometimes_low","often_low","unknown"].includes(String(draft.hydration_pattern))) setHydrationPattern(draft.hydration_pattern as typeof hydrationPattern);
        if (["independent","needs_reminder","needs_setup","needs_assistance","unknown"].includes(String(draft.eating_independence))) setEatingIndependence(draft.eating_independence as typeof eatingIndependence);
        if (["none","sometimes","daily","unknown"].includes(String(draft.caregiver_support))) setCaregiverSupport(draft.caregiver_support as typeof caregiverSupport);
      }
    } catch {
      // Ignore malformed local draft; assessment remains usable.
    } finally {
      setElderlyDraftLoaded(true);
    }
  }, [stage]);

  useEffect(() => {
    if (stage !== "elderly" || !elderlyDraftLoaded || typeof window === "undefined") return;
    sessionStorage.setItem(
      "sehatin:nutrition-assessment-draft:elderly",
      JSON.stringify({ has_condition: hasCondition, conditions, other_condition: otherCondition, hydration_pattern: hydrationPattern, eating_independence: eatingIndependence, caregiver_support: caregiverSupport }),
    );
  }, [caregiverSupport, conditions, eatingIndependence, elderlyDraftLoaded, hasCondition, hydrationPattern, otherCondition, stage]);

  const childAgeMonths = useMemo(
    () => (stage === "elderly" ? null : calculateAgeMonths(dateOfBirth, assessmentDate)),
    [assessmentDate, dateOfBirth, stage],
  );

  const ageRange = useMemo(() => {
    if (stage === "mpasi") return { min: 6, max: 23, unit: "bulan" };
    if (stage === "toddler") return { min: 24, max: 59, unit: "bulan" };
    return { min: 60, max: 120, unit: "tahun" };
  }, [stage]);

  const anthropometricPayload = useCallback(() => {
    const numericAge = stage === "elderly" ? Number(age) : childAgeMonths;
    const numericWeight = Number(weight);
    const numericHeight = Number(height);
    if (!sex || numericAge === null || !Number.isFinite(numericAge) || !Number.isFinite(numericWeight) || !Number.isFinite(numericHeight) || numericWeight <= 0 || numericHeight <= 0) return null;
    return {
      stage,
      ...(stage === "elderly"
        ? { age_years: numericAge }
        : { date_of_birth: dateOfBirth, assessment_date: assessmentDate, age_months: numericAge }),
      sex,
      weight_kg: numericWeight,
      height_cm: numericHeight,
    };
  }, [age, assessmentDate, childAgeMonths, dateOfBirth, height, sex, stage, weight]);

  const runAnthropometricValidation = useCallback(async (signal?: AbortSignal) => {
    const payload = anthropometricPayload();
    if (!payload) return null;
    setValidationLoading(true);
    setValidationError("");
    try {
      const result = await apiFetch<NutritionValidation>("/api/nutrition/validate", {
        method: "POST",
        body: JSON.stringify(payload),
        signal,
        timeoutMs: 10_000,
      });
      setValidation(result);
      return result;
    } catch (err) {
      if (signal?.aborted) return null;
      setValidation(null);
      setValidationError(err instanceof Error ? err.message : "Validasi pengukuran belum dapat dilakukan.");
      return null;
    } finally {
      if (!signal?.aborted) setValidationLoading(false);
    }
  }, [anthropometricPayload]);

  const localValidationMessage = useCallback((current: number) => {
    const numericAge = stage === "elderly" ? Number(age) : childAgeMonths;
    if (current === 0) {
      if (stage !== "elderly" && !dateOfBirth) return "Masukkan tanggal lahir agar usia dihitung otomatis.";
      if (numericAge === null || !Number.isFinite(numericAge) || numericAge < ageRange.min || numericAge > ageRange.max) {
        if (stage === "mpasi" && numericAge !== null && numericAge >= 24) return "Usia sudah 24 bulan atau lebih. Gunakan kategori Toddler.";
        if (stage === "toddler" && numericAge !== null && numericAge < 24) return "Usia di bawah 24 bulan. Gunakan kategori MPASI.";
        return `Usia harus berada pada rentang ${ageRange.min}–${ageRange.max} ${ageRange.unit}.`;
      }
      if (!sex) return "Pilih jenis kelamin karena referensi pertumbuhan/kebutuhan menggunakan kelompok yang sesuai.";
      if (!weight || !Number.isFinite(Number(weight)) || Number(weight) <= 0) return "Masukkan berat badan dalam kilogram.";
      if (!height || !Number.isFinite(Number(height)) || Number(height) <= 0) return `Masukkan ${stage === "elderly" ? "tinggi badan" : "panjang/tinggi badan"} dalam sentimeter.`;
    }
    if (current === 1) {
      if (stage === "mpasi" && !feedingMode) return "Pilih pola pemberian ASI/formula agar baseline MPASI tidak menggunakan asumsi yang salah.";
      const frequency = Number(mealFrequency);
      if (!Number.isFinite(frequency) || frequency < 1 || frequency > 10) return "Frekuensi makan harus 1–10 kali per hari.";
      if (stage === "elderly" && chewingDifficulty === null) return "Pilih apakah lansia mengalami kesulitan mengunyah.";
      if (stage === "elderly" && swallowingDifficulty === null) return "Pilih apakah lansia mengalami kesulitan menelan.";
    }
    if (current === 2 && stage === "elderly") {
      if (hasCondition === null) return "Pilih apakah lansia memiliki penyakit atau kondisi kesehatan yang sudah diketahui.";
      if (hasCondition && conditions.length === 0) return "Pilih minimal satu penyakit atau kondisi kesehatan.";
      if (hasCondition && conditions.includes("other") && !otherCondition.trim()) return "Isi nama penyakit atau kondisi ketika memilih Lainnya.";
    }
    return "";
  }, [age, ageRange.max, ageRange.min, ageRange.unit, chewingDifficulty, childAgeMonths, conditions, dateOfBirth, feedingMode, hasCondition, height, mealFrequency, otherCondition, sex, stage, swallowingDifficulty, weight]);

  function validateLocalStep(current: number) {
    const message = localValidationMessage(current);
    setValidationAttempted(true);
    setError(message);
    return !message;
  }

  useEffect(() => {
    if (!validationAttempted) return;
    const message = localValidationMessage(step);
    if (message) {
      setError(message);
      return;
    }
    if (step === 0 && validation && !validation.can_process) {
      setError(validation.message);
      return;
    }
    setError("");
  }, [localValidationMessage, step, validation, validationAttempted]);

  async function next() {
    if (!validateLocalStep(step)) return;
    if (step === 0) {
      const latest = await runAnthropometricValidation();
      if (!latest) {
        setError("Validasi pengukuran belum berhasil. Pastikan backend tersedia lalu coba lagi.");
        return;
      }
      if (!latest.can_process) {
        setError(latest.message);
        return;
      }
    }
    setValidationAttempted(false);
    setError("");
    setStep((value) => Math.min(finalStep, value + 1));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function back() {
    setError("");
    setValidationAttempted(false);
    setStep((value) => Math.max(0, value - 1));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function buildPayload(): NutritionAssessmentPayload | null {
    if (!sex || !weight || !height) return null;
    if (stage !== "elderly" && childAgeMonths === null) return null;
    const payload: NutritionAssessmentPayload = {
      stage,
      sex,
      weight_kg: Number(weight),
      height_cm: Number(height),
      allergies: listFromText(allergies),
      dietary_restrictions: listFromText(restrictions),
      medical_context: medicalContext.trim() || undefined,
      notes: notes.trim() || undefined,
      appetite,
      meal_frequency: Number(mealFrequency),
    };
    if (stage === "elderly") {
      payload.age_years = Number(age);
      payload.activity_level = activityLevel;
      payload.hydration_pattern = hydrationPattern;
      payload.eating_independence = eatingIndependence;
      payload.caregiver_support = caregiverSupport;
      payload.chewing_difficulty = chewingDifficulty === true;
      payload.swallowing_difficulty = swallowingDifficulty === true;
      payload.has_condition = hasCondition === true;
      payload.conditions = hasCondition ? conditions : [];
      payload.other_condition = hasCondition && conditions.includes("other") ? otherCondition.trim() : undefined;
      return payload;
    }

    payload.date_of_birth = dateOfBirth;
    payload.assessment_date = assessmentDate;
    payload.age_months = childAgeMonths ?? undefined;
    payload.snack_frequency = Number(snackFrequency);
    payload.animal_source_food_days = Number(animalSourceFoodDays);
    payload.fruit_vegetable_days = Number(fruitVegetableDays);
    payload.recent_food_groups = recentFoodGroups;
    payload.recent_food_group_count = recentFoodGroups.length;
    payload.responsive_feeding = responsiveFeeding;
    payload.meal_routine = mealRoutine;
    payload.food_rejection = foodRejection;
    payload.food_refusal = foodRejection !== "none";
    payload.food_rejection_details = listFromText(foodRejectionDetails);
    payload.feeding_difficulty = feedingDifficulty;
    payload.feeding_difficulty_details = listFromText(feedingDifficultyDetails);
    payload.barriers = listFromText(barriers);

    if (stage === "mpasi") {
      payload.feeding_mode = feedingMode as NutritionAssessmentPayload["feeding_mode"];
      payload.mpasi_history = mpasiHistory;
      payload.texture_level = textureLevel as NutritionAssessmentPayload["texture_level"];
      payload.feeding_method = feedingMethod;
      payload.texture_refusal = textureRefusal;
      payload.safety_hygiene_ok = safetyHygieneOk;
    } else {
      payload.pressure_to_eat = pressureToEat;
      payload.screen_during_meals = screenDuringMeals;
      payload.self_feeding_opportunity = selfFeedingOpportunity;
      payload.meal_environment = mealEnvironment;
      payload.mealtime_duration_minutes = Number(mealtimeDuration);
      payload.food_preferences = listFromText(foodPreferences);
      payload.sweetened_beverage_exposure = sweetenedBeverageExposure;
      payload.sweet_beverage_days = sweetenedBeverageExposure ? Number(sweetBeverageDays) : 0;
      payload.repeated_exposure_days = Number(repeatedExposureDays);
      payload.water_primary_beverage = waterPrimaryBeverage;
    }
    return payload;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!validateLocalStep(0) || !validateLocalStep(1) || !validateLocalStep(2)) return;
    const latest = await runAnthropometricValidation();
    if (!latest || !latest.can_process) {
      setError(latest?.message ?? "Validasi pengukuran belum berhasil.");
      return;
    }
    const payload = buildPayload();
    if (!payload) {
      setError("Assessment belum lengkap.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await apiFetch<NutritionResult>("/api/nutrition/recommendation", { method: "POST", body: JSON.stringify(payload) });
      saveNutritionResult(result, payload);
      router.push(nutritionResultPath(stage));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rekomendasi belum dapat dibuat. Silakan coba lagi.");
      setLoading(false);
    }
  }

  const numericAge = stage === "elderly" ? Number(age) : childAgeMonths;
  const fieldErrors = validationAttempted ? {
    age: (numericAge === null || !Number.isFinite(numericAge) || numericAge < ageRange.min || numericAge > ageRange.max) ? `Gunakan rentang ${ageRange.min}–${ageRange.max} ${ageRange.unit}.` : "",
    dateOfBirth: stage !== "elderly" && !dateOfBirth ? "Tanggal lahir wajib diisi." : "",
    sex: !sex ? "Pilih jenis kelamin." : "",
    weight: (!weight || !Number.isFinite(Number(weight)) || Number(weight) <= 0) ? "Masukkan berat badan yang valid." : "",
    height: (!height || !Number.isFinite(Number(height)) || Number(height) <= 0) ? "Masukkan tinggi/panjang yang valid." : "",
    feedingMode: stage === "mpasi" && !feedingMode ? "Pilih pola pemberian susu." : "",
    mealFrequency: (!Number.isFinite(Number(mealFrequency)) || Number(mealFrequency) < 1 || Number(mealFrequency) > 10) ? "Masukkan frekuensi 1–10 kali per hari." : "",
  } : { age: "", dateOfBirth: "", sex: "", weight: "", height: "", feedingMode: "", mealFrequency: "" };

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl" aria-live="polite" aria-busy="true">
        <div className="processing-line overflow-hidden rounded-lg border border-line bg-surface p-7 shadow-subtle md:p-10">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-light text-primary-dark"><Loader2 className="animate-spin" size={22} /></div>
          <p className="eyebrow mt-8">Processing</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em] md:text-4xl">Preparing your nutrition guidance...</h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-secondary">Memvalidasi pengukuran, membentuk baseline terstruktur, memilih gap perilaku utama, lalu menyusun kandidat target sebelum halaman hasil dibuka.</p>
          <div className="mt-8 grid gap-3 sm:grid-cols-4">{["Validate", "Normalize baseline", "Detect gap", "Target candidates"].map((label, index) => <div key={label} className="border-t border-line pt-3"><p className="text-xs font-bold text-primary-dark">0{index + 1}</p><p className="mt-1 text-sm text-secondary">{label}</p></div>)}</div>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-5xl">
      <div className="grid gap-8 lg:grid-cols-[250px_1fr] lg:items-start">
        <aside className="lg:sticky lg:top-24">
          <p className="eyebrow">Assessment progress</p>
          <div className="step-rail mt-4" aria-hidden="true">{steps.map((_, index) => <span key={index} className={index <= step ? "active" : ""} />)}</div>
          <p className="mt-4 text-2xl font-semibold tracking-[-0.03em]">{steps[step]}</p>
          <p className="mt-2 text-sm leading-6 text-secondary">Langkah {step + 1} dari {steps.length}. Data dikumpulkan di form terlebih dahulu; server hanya dipanggil saat validasi eksplisit atau analisis.</p>
          <ol className="mt-7 hidden space-y-4 lg:block">{steps.map((label, index) => <li key={label} className={`flex items-center gap-3 text-sm ${index === step ? "font-semibold text-primary-dark" : index < step ? "text-secondary" : "text-muted"}`}><span className={`flex h-7 w-7 items-center justify-center rounded-full border text-xs ${index < step ? "border-primary bg-primary text-white" : index === step ? "border-primary text-primary-dark" : "border-line"}`}>{index < step ? <Check size={14} /> : index + 1}</span>{label}</li>)}</ol>
        </aside>

        <div className="min-w-0">
          <div className="rounded-lg border border-line bg-surface p-6 shadow-subtle md:p-8">
            {step === 0 && <BasicStep stage={stage} age={age} setAge={setAge} dateOfBirth={dateOfBirth} setDateOfBirth={setDateOfBirth} assessmentDate={assessmentDate} childAgeMonths={childAgeMonths} sex={sex} setSex={setSex} weight={weight} setWeight={setWeight} height={height} setHeight={setHeight} ageRange={ageRange} validation={validation} validationLoading={validationLoading} validationError={validationError} fieldErrors={fieldErrors} />}
            {step === 1 && stage === "mpasi" && <MpasiEatingStep feedingMode={feedingMode} setFeedingMode={setFeedingMode} mpasiHistory={mpasiHistory} setMpasiHistory={setMpasiHistory} mealFrequency={mealFrequency} setMealFrequency={setMealFrequency} snackFrequency={snackFrequency} setSnackFrequency={setSnackFrequency} mealRoutine={mealRoutine} setMealRoutine={setMealRoutine} animalSourceFoodDays={animalSourceFoodDays} setAnimalSourceFoodDays={setAnimalSourceFoodDays} fruitVegetableDays={fruitVegetableDays} setFruitVegetableDays={setFruitVegetableDays} recentFoodGroups={recentFoodGroups} setRecentFoodGroups={setRecentFoodGroups} textureLevel={textureLevel} setTextureLevel={setTextureLevel} fieldErrors={fieldErrors} />}
            {step === 1 && stage === "toddler" && <ToddlerEatingStep mealFrequency={mealFrequency} setMealFrequency={setMealFrequency} snackFrequency={snackFrequency} setSnackFrequency={setSnackFrequency} mealRoutine={mealRoutine} setMealRoutine={setMealRoutine} mealtimeDuration={mealtimeDuration} setMealtimeDuration={setMealtimeDuration} animalSourceFoodDays={animalSourceFoodDays} setAnimalSourceFoodDays={setAnimalSourceFoodDays} fruitVegetableDays={fruitVegetableDays} setFruitVegetableDays={setFruitVegetableDays} recentFoodGroups={recentFoodGroups} setRecentFoodGroups={setRecentFoodGroups} foodPreferences={foodPreferences} setFoodPreferences={setFoodPreferences} fieldErrors={fieldErrors} />}
            {step === 1 && stage === "elderly" && <ElderlyEatingStep appetite={appetite} setAppetite={setAppetite} mealFrequency={mealFrequency} setMealFrequency={setMealFrequency} activityLevel={activityLevel} setActivityLevel={setActivityLevel} hydrationPattern={hydrationPattern} setHydrationPattern={setHydrationPattern} eatingIndependence={eatingIndependence} setEatingIndependence={setEatingIndependence} caregiverSupport={caregiverSupport} setCaregiverSupport={setCaregiverSupport} chewingDifficulty={chewingDifficulty} setChewingDifficulty={setChewingDifficulty} swallowingDifficulty={swallowingDifficulty} setSwallowingDifficulty={setSwallowingDifficulty} fieldErrors={fieldErrors} />}
            {step === 2 && stage !== "elderly" && <ChildContextStep stage={stage} appetite={appetite} setAppetite={setAppetite} responsiveFeeding={responsiveFeeding} setResponsiveFeeding={setResponsiveFeeding} feedingMethod={feedingMethod} setFeedingMethod={setFeedingMethod} foodRejection={foodRejection} setFoodRejection={setFoodRejection} foodRejectionDetails={foodRejectionDetails} setFoodRejectionDetails={setFoodRejectionDetails} feedingDifficulty={feedingDifficulty} setFeedingDifficulty={setFeedingDifficulty} feedingDifficultyDetails={feedingDifficultyDetails} setFeedingDifficultyDetails={setFeedingDifficultyDetails} textureRefusal={textureRefusal} setTextureRefusal={setTextureRefusal} pressureToEat={pressureToEat} setPressureToEat={setPressureToEat} screenDuringMeals={screenDuringMeals} setScreenDuringMeals={setScreenDuringMeals} selfFeedingOpportunity={selfFeedingOpportunity} setSelfFeedingOpportunity={setSelfFeedingOpportunity} mealEnvironment={mealEnvironment} setMealEnvironment={setMealEnvironment} sweetenedBeverageExposure={sweetenedBeverageExposure} setSweetenedBeverageExposure={setSweetenedBeverageExposure} sweetBeverageDays={sweetBeverageDays} setSweetBeverageDays={setSweetBeverageDays} repeatedExposureDays={repeatedExposureDays} setRepeatedExposureDays={setRepeatedExposureDays} waterPrimaryBeverage={waterPrimaryBeverage} setWaterPrimaryBeverage={setWaterPrimaryBeverage} safetyHygieneOk={safetyHygieneOk} setSafetyHygieneOk={setSafetyHygieneOk} barriers={barriers} setBarriers={setBarriers} allergies={allergies} setAllergies={setAllergies} restrictions={restrictions} setRestrictions={setRestrictions} medicalContext={medicalContext} setMedicalContext={setMedicalContext} notes={notes} setNotes={setNotes} />}
            {step === 2 && stage === "elderly" && <ElderlyHealthConditionStep hasCondition={hasCondition} setHasCondition={(value) => { setHasCondition(value); if (!value) { setConditions([]); setOtherCondition(""); } }} conditions={conditions} setConditions={setConditions} otherCondition={otherCondition} setOtherCondition={setOtherCondition} validationAttempted={validationAttempted} />}
            {step === 3 && stage === "elderly" && <ElderlyDietaryStep allergies={allergies} setAllergies={setAllergies} restrictions={restrictions} setRestrictions={setRestrictions} medicalContext={medicalContext} setMedicalContext={setMedicalContext} notes={notes} setNotes={setNotes} />}
            {step === 3 && stage !== "elderly" && <ReviewStep reviewIndex="04" stage={stage} age={String(childAgeMonths ?? "-")} unit={ageRange.unit} dateOfBirth={dateOfBirth} ageBand={childBand(stage, childAgeMonths)} sex={sex} weight={weight} height={height} feedingMode={feedingMode} appetite={appetite} mealFrequency={mealFrequency} allergies={allergies} restrictions={restrictions} medicalContext={medicalContext} hasCondition={hasCondition} conditions={conditions} otherCondition={otherCondition} validation={validation} />}
            {step === 4 && stage === "elderly" && <ReviewStep reviewIndex="05" stage={stage} age={age} unit={ageRange.unit} dateOfBirth={dateOfBirth} ageBand="" sex={sex} weight={weight} height={height} feedingMode={feedingMode} appetite={appetite} mealFrequency={mealFrequency} hydrationPattern={hydrationPattern} eatingIndependence={eatingIndependence} caregiverSupport={caregiverSupport} allergies={allergies} restrictions={restrictions} medicalContext={medicalContext} hasCondition={hasCondition} conditions={conditions} otherCondition={otherCondition} validation={validation} />}
          </div>
          {error && <div className="mt-5"><Alert variant="error" title="Periksa assessment">{error}</Alert></div>}
          <div className="mt-6 flex flex-col-reverse justify-between gap-3 sm:flex-row">
            {step > 0 ? <Button type="button" variant="ghost" onClick={back}><ArrowLeft size={17} /> Kembali</Button> : <span />}
            {step < finalStep ? <Button type="button" size="lg" onClick={() => void next()} isLoading={step === 0 && validationLoading}>Lanjut <ArrowRight size={17} /></Button> : <Button type="submit" size="lg">Analyze My Nutrition <ArrowRight size={17} /></Button>}
          </div>
        </div>
      </div>
    </form>
  );
}

function StepHeading({ index, title, body }: { index: string; title: string; body: string }) {
  return <div className="mb-7"><p className="eyebrow">Step {index}</p><h2 className="mt-3 text-3xl font-semibold tracking-[-0.04em]">{title}</h2><p className="mt-3 max-w-2xl text-sm leading-6 text-secondary">{body}</p></div>;
}

type FieldErrors = { age: string; dateOfBirth: string; sex: string; weight: string; height: string; feedingMode: string; mealFrequency: string };
type BasicStepProps = {
  stage: NutritionStage; age: string; setAge: (value: string) => void; dateOfBirth: string; setDateOfBirth: (value: string) => void; assessmentDate: string; childAgeMonths: number | null;
  sex: "" | "female" | "male"; setSex: (value: "" | "female" | "male") => void; weight: string; setWeight: (value: string) => void; height: string; setHeight: (value: string) => void;
  ageRange: { min: number; max: number; unit: string }; validation: NutritionValidation | null; validationLoading: boolean; validationError: string; fieldErrors: FieldErrors;
};

function BasicStep({ stage, age, setAge, dateOfBirth, setDateOfBirth, assessmentDate, childAgeMonths, sex, setSex, weight, setWeight, height, setHeight, ageRange, validation, validationLoading, validationError, fieldErrors }: BasicStepProps) {
  const child = stage !== "elderly";
  return <><StepHeading index="01" title={child ? "Tentang anak" : "Basic Information"} body={child ? "Tanggal lahir digunakan untuk menghitung usia secara otomatis pada tanggal assessment; usia tidak perlu diketik manual." : "Usia, jenis kelamin, berat, dan tinggi dibaca bersama sebagai konteks panduan."} />
    <div className="grid gap-5 grid-cols-1">
      {child ? <Input label="Tanggal lahir" type="date" value={dateOfBirth} max={assessmentDate} onChange={(e) => setDateOfBirth(e.target.value)} required error={fieldErrors.dateOfBirth || fieldErrors.age || undefined} helperText={childAgeMonths === null ? `Assessment: ${assessmentDate}` : `Usia terhitung: ${childAgeMonths} bulan · ${childBand(stage, childAgeMonths)}`} /> : <Input label={`Usia (${ageRange.unit})`} type="number" min={ageRange.min} max={ageRange.max} value={age} onChange={(e) => setAge(e.target.value)} required error={fieldErrors.age || undefined} />}
      <Select label="Jenis kelamin" required value={sex} onChange={(e) => setSex(e.target.value as BasicStepProps["sex"])} error={fieldErrors.sex || undefined} options={[{ value: "", label: "Pilih" }, { value: "female", label: "Perempuan" }, { value: "male", label: "Laki-laki" }]} helperText={child ? "Digunakan untuk memilih referensi pertumbuhan yang sesuai." : "Digunakan untuk memilih kelompok referensi kebutuhan gizi."} />
      <Input label="Berat badan (kg)" type="number" step="0.1" min="0.1" max="300" value={weight} onChange={(e) => setWeight(e.target.value)} required error={fieldErrors.weight || undefined} helperText="Masukkan hasil pengukuran dalam kilogram." />
      <Input label={child ? "Panjang/Tinggi badan (cm)" : "Tinggi badan (cm)"} type="number" step="0.1" min="1" max="250" value={height} onChange={(e) => setHeight(e.target.value)} required error={fieldErrors.height || undefined} helperText={child ? "Gunakan hasil pengukuran terbaru dalam sentimeter." : "Digunakan sebagai konteks ukuran tubuh, bukan diagnosis."} />
    </div>
    <div className="mt-6" aria-live="polite">{validationLoading && <div className="flex items-center gap-2 text-sm text-secondary"><Loader2 size={16} className="animate-spin" /> Memeriksa konsistensi pengukuran...</div>}{!validationLoading && validation && <Alert variant={validationVariant(validation.status)} title={validation.status === "VALID" ? "Data dapat diproses" : validation.status === "WARNING" ? "Periksa kembali pengukuran" : "Data belum dapat diproses"}>{validation.message}</Alert>}{!validationLoading && validation?.issues.length ? <ul className="mt-3 space-y-2 text-xs leading-5 text-secondary">{validation.issues.map((issue) => <li key={issue.code} className="flex gap-2"><span aria-hidden="true">{issue.level === "WARNING" ? "⚠" : issue.level === "INVALID" ? "×" : "✓"}</span><span>{issue.message}</span></li>)}</ul> : null}{!validationLoading && validationError && <Alert variant="warning" title="Validasi server belum tersedia">{validationError}</Alert>}{validation?.references?.length ? <div className="mt-4 flex items-center gap-2 text-xs text-muted"><ShieldCheck size={15} aria-hidden="true" /><span>{child ? "Validasi anak menggunakan referensi pertumbuhan yang sudah tersedia di SEHATIN." : "BMI hanya digunakan sebagai konteks konsistensi input."}</span></div> : null}</div>
  </>;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <h3 className="col-span-full border-b border-line pb-2 text-xs font-black uppercase tracking-[.12em] text-primary-dark">{children}</h3>;
}

function MultiSelectFoodGroups({ values, onChange, label }: { values: NutritionFoodGroup[]; onChange: (values: NutritionFoodGroup[]) => void; label: string }) {
  return <fieldset className="col-span-full"><legend className="text-sm font-medium text-text">{label}</legend><p className="mt-1 text-xs text-muted">Pilih semua yang sesuai. Data disimpan sebagai multi-select terstruktur.</p><div className="mt-3 grid gap-2 grid-cols-1">{FOOD_GROUP_OPTIONS.map((option) => { const checked = values.includes(option.value); return <label key={option.value} className={`flex min-h-12 cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 text-sm font-medium ${checked ? "border-primary/50 bg-primary-light/45" : "border-line bg-background hover:border-primary/30"}`}><input type="checkbox" checked={checked} onChange={() => onChange(checked ? values.filter((item) => item !== option.value) : [...values, option.value])} className="h-4 w-4 shrink-0 accent-primary" /><span>{option.label}</span></label>; })}</div></fieldset>;
}

type EatingShared = { mealFrequency: string; setMealFrequency: (value: string) => void; snackFrequency: string; setSnackFrequency: (value: string) => void; mealRoutine: "regular" | "mixed" | "irregular"; setMealRoutine: (value: "regular" | "mixed" | "irregular") => void; animalSourceFoodDays: string; setAnimalSourceFoodDays: (value: string) => void; fruitVegetableDays: string; setFruitVegetableDays: (value: string) => void; recentFoodGroups: NutritionFoodGroup[]; setRecentFoodGroups: (value: NutritionFoodGroup[]) => void; fieldErrors: FieldErrors };

type MpasiEatingProps = EatingShared & { feedingMode: string; setFeedingMode: (value: string) => void; mpasiHistory: "not_started" | "started"; setMpasiHistory: (value: "not_started" | "started") => void; textureLevel: string; setTextureLevel: (value: string) => void };
function MpasiEatingStep(props: MpasiEatingProps) {
  return <><StepHeading index="02" title="Eating Context · MPASI" body="Profile MPASI berfokus pada feeding context, frekuensi, kelompok pangan, dan tekstur untuk usia 6–23 bulan." /><div className="grid gap-5 grid-cols-1">
    <SectionLabel>Feeding context</SectionLabel>
    <Select label="Pola pemberian susu" required value={props.feedingMode} onChange={(e) => props.setFeedingMode(e.target.value)} error={props.fieldErrors.feedingMode || undefined} options={[{ value: "", label: "Pilih" }, { value: "breastmilk", label: "ASI" }, { value: "formula", label: "Formula" }, { value: "mixed", label: "ASI + formula" }, { value: "other", label: "Lainnya" }]} />
    <Select label="Riwayat MPASI" value={props.mpasiHistory} onChange={(e) => props.setMpasiHistory(e.target.value as MpasiEatingProps["mpasiHistory"])} options={[{ value: "started", label: "Sudah mulai MPASI" }, { value: "not_started", label: "Belum mulai MPASI" }]} />
    <SectionLabel>Pola makan</SectionLabel>
    <Input label="Frekuensi makan utama per hari" type="number" min="1" max="10" value={props.mealFrequency} onChange={(e) => props.setMealFrequency(e.target.value)} error={props.fieldErrors.mealFrequency || undefined} />
    <Input label="Frekuensi snack/camilan per hari" type="number" min="0" max="10" value={props.snackFrequency} onChange={(e) => props.setSnackFrequency(e.target.value)} />
    <Select label="Keteraturan waktu makan" value={props.mealRoutine} onChange={(e) => props.setMealRoutine(e.target.value as MpasiEatingProps["mealRoutine"])} options={[{ value: "regular", label: "Teratur" }, { value: "mixed", label: "Kadang teratur" }, { value: "irregular", label: "Belum teratur" }]} />
    <Select label="Tekstur saat ini" value={props.textureLevel} onChange={(e) => props.setTextureLevel(e.target.value)} options={[{ value: "smooth_mashed", label: "Lumat halus/kental" }, { value: "mashed_lumpy", label: "Lumat lebih kasar" }, { value: "finger_food", label: "Finger food aman" }, { value: "family_soft", label: "Makanan keluarga lunak" }]} />
    <SectionLabel>Makanan yang diberikan</SectionLabel>
    <Input label="Hari dengan sumber protein hewani (0–7)" type="number" min="0" max="7" value={props.animalSourceFoodDays} onChange={(e) => props.setAnimalSourceFoodDays(e.target.value)} />
    <Input label="Hari dengan kesempatan sayur/buah (0–7)" type="number" min="0" max="7" value={props.fruitVegetableDays} onChange={(e) => props.setFruitVegetableDays(e.target.value)} />
    <MultiSelectFoodGroups values={props.recentFoodGroups} onChange={props.setRecentFoodGroups} label="Kelompok pangan yang dikonsumsi pada hari pengamatan" />
  </div></>;
}

type ToddlerEatingProps = EatingShared & { mealtimeDuration: string; setMealtimeDuration: (value: string) => void; foodPreferences: string; setFoodPreferences: (value: string) => void };
function ToddlerEatingStep(props: ToddlerEatingProps) {
  return <><StepHeading index="02" title="Eating Context · Toddler" body="Profile Toddler berfokus pada healthy eating habit: ritme makan, variasi, preferensi, dan kesempatan paparan makanan." /><div className="grid gap-5 grid-cols-1">
    <SectionLabel>Rutinitas makan</SectionLabel>
    <Select label="Keteraturan makan utama" value={props.mealRoutine} onChange={(e) => props.setMealRoutine(e.target.value as ToddlerEatingProps["mealRoutine"])} options={[{ value: "regular", label: "Teratur" }, { value: "mixed", label: "Kadang teratur" }, { value: "irregular", label: "Belum teratur" }]} />
    <Input label="Frekuensi makan utama per hari" type="number" min="1" max="10" value={props.mealFrequency} onChange={(e) => props.setMealFrequency(e.target.value)} error={props.fieldErrors.mealFrequency || undefined} />
    <Input label="Frekuensi snack/camilan per hari" type="number" min="0" max="10" value={props.snackFrequency} onChange={(e) => props.setSnackFrequency(e.target.value)} />
    <Input label="Durasi makan rata-rata (menit)" type="number" min="1" max="180" value={props.mealtimeDuration} onChange={(e) => props.setMealtimeDuration(e.target.value)} />
    <SectionLabel>Variasi makanan</SectionLabel>
    <Input label="Hari dengan sumber protein hewani (0–7)" type="number" min="0" max="7" value={props.animalSourceFoodDays} onChange={(e) => props.setAnimalSourceFoodDays(e.target.value)} />
    <Input label="Hari dengan kesempatan sayur/buah (0–7)" type="number" min="0" max="7" value={props.fruitVegetableDays} onChange={(e) => props.setFruitVegetableDays(e.target.value)} />
    <MultiSelectFoodGroups values={props.recentFoodGroups} onChange={props.setRecentFoodGroups} label="Kelompok makanan yang biasa diterima" />
    <div className="col-span-full"><Input label="Makanan yang disukai" value={props.foodPreferences} onChange={(e) => props.setFoodPreferences(e.target.value)} placeholder="Contoh: telur, tempe, pisang" helperText="Pisahkan dengan koma. Disimpan sebagai daftar terstruktur." /></div>
  </div></>;
}

type ChildContextProps = {
  stage: NutritionStage; appetite: "low" | "typical" | "high"; setAppetite: (value: "low" | "typical" | "high") => void; responsiveFeeding: "usually" | "sometimes" | "rarely"; setResponsiveFeeding: (value: "usually" | "sometimes" | "rarely") => void; feedingMethod: "caregiver_assisted" | "mixed" | "self_feeding"; setFeedingMethod: (value: "caregiver_assisted" | "mixed" | "self_feeding") => void;
  foodRejection: "none" | "occasional" | "frequent"; setFoodRejection: (value: "none" | "occasional" | "frequent") => void; foodRejectionDetails: string; setFoodRejectionDetails: (value: string) => void; feedingDifficulty: "none" | "some" | "significant"; setFeedingDifficulty: (value: "none" | "some" | "significant") => void; feedingDifficultyDetails: string; setFeedingDifficultyDetails: (value: string) => void;
  textureRefusal: boolean; setTextureRefusal: (value: boolean) => void; pressureToEat: boolean; setPressureToEat: (value: boolean) => void; screenDuringMeals: boolean; setScreenDuringMeals: (value: boolean) => void; selfFeedingOpportunity: boolean; setSelfFeedingOpportunity: (value: boolean) => void; mealEnvironment: "calm" | "mixed" | "distracted"; setMealEnvironment: (value: "calm" | "mixed" | "distracted") => void;
  sweetenedBeverageExposure: boolean; setSweetenedBeverageExposure: (value: boolean) => void; sweetBeverageDays: string; setSweetBeverageDays: (value: string) => void; repeatedExposureDays: string; setRepeatedExposureDays: (value: string) => void; waterPrimaryBeverage: boolean; setWaterPrimaryBeverage: (value: boolean) => void; safetyHygieneOk: boolean; setSafetyHygieneOk: (value: boolean) => void; barriers: string; setBarriers: (value: string) => void;
  allergies: string; setAllergies: (value: string) => void; restrictions: string; setRestrictions: (value: string) => void; medicalContext: string; setMedicalContext: (value: string) => void; notes: string; setNotes: (value: string) => void;
};
function ChildContextStep(props: ChildContextProps) {
  const toddler = props.stage === "toddler";
  return <><StepHeading index="03" title={toddler ? "Perilaku makan, minuman & kendala" : "Cara makan, kendala & safety"} body="Pertanyaan lanjutan muncul hanya ketika relevan. Semua perubahan tetap lokal sampai kamu menekan Analyze My Nutrition." /><div className="grid gap-5 grid-cols-1">
    <SectionLabel>Perilaku saat makan</SectionLabel>
    <Select label="Responsive feeding saat ini" value={props.responsiveFeeding} onChange={(e) => props.setResponsiveFeeding(e.target.value as ChildContextProps["responsiveFeeding"])} options={[{ value: "usually", label: "Biasanya dilakukan" }, { value: "sometimes", label: "Kadang dilakukan" }, { value: "rarely", label: "Jarang dilakukan" }]} />
    <Select label="Nafsu makan" value={props.appetite} onChange={(e) => props.setAppetite(e.target.value as ChildContextProps["appetite"])} options={appetiteOptions} />
    {!toddler && <Select label="Cara makan saat ini" value={props.feedingMethod} onChange={(e) => props.setFeedingMethod(e.target.value as ChildContextProps["feedingMethod"])} options={[{ value: "caregiver_assisted", label: "Dibantu caregiver" }, { value: "mixed", label: "Campuran dibantu + mandiri" }, { value: "self_feeding", label: "Lebih banyak makan mandiri" }]} />}
    <Select label="Penolakan makanan" value={props.foodRejection} onChange={(e) => props.setFoodRejection(e.target.value as ChildContextProps["foodRejection"])} options={[{ value: "none", label: "Tidak ada / jarang" }, { value: "occasional", label: "Kadang" }, { value: "frequent", label: "Sering" }]} />
    {props.foodRejection !== "none" && <div className="col-span-full"><Input label="Makanan yang sering ditolak" value={props.foodRejectionDetails} onChange={(e) => props.setFoodRejectionDetails(e.target.value)} placeholder="Contoh: sayur hijau, telur" helperText="Pisahkan dengan koma." /></div>}
    <Select label="Kesulitan makan" value={props.feedingDifficulty} onChange={(e) => props.setFeedingDifficulty(e.target.value as ChildContextProps["feedingDifficulty"])} options={[{ value: "none", label: "Tidak ada kendala berarti" }, { value: "some", label: "Cukup sulit" }, { value: "significant", label: "Sering menghambat makan" }]} />
    {props.feedingDifficulty !== "none" && <div className="col-span-full"><Input label="Jenis kesulitan yang dirasakan" value={props.feedingDifficultyDetails} onChange={(e) => props.setFeedingDifficultyDetails(e.target.value)} placeholder="Contoh: sulit duduk tenang, menolak tekstur tertentu" helperText="Ini observasi pengalaman caregiver, bukan diagnosis." /></div>}
    {toddler ? <><CheckRow label="Sering memberi tekanan agar anak makan" checked={props.pressureToEat} onChange={props.setPressureToEat} /><CheckRow label="Makan sering disertai screen" checked={props.screenDuringMeals} onChange={props.setScreenDuringMeals} /><CheckRow label="Anak mendapat kesempatan makan mandiri" checked={props.selfFeedingOpportunity} onChange={props.setSelfFeedingOpportunity} /><Select label="Lingkungan makan" value={props.mealEnvironment} onChange={(e) => props.setMealEnvironment(e.target.value as ChildContextProps["mealEnvironment"])} options={[{ value: "calm", label: "Tenang/fokus makan" }, { value: "mixed", label: "Campuran" }, { value: "distracted", label: "Sering terdistraksi" }]} /></> : <><CheckRow label="Tekstur tertentu sering ditolak" checked={props.textureRefusal} onChange={props.setTextureRefusal} /><CheckRow label="Persiapan makanan dan kebersihan dilakukan dengan aman" checked={props.safetyHygieneOk} onChange={props.setSafetyHygieneOk} /></>}
    {toddler && <><SectionLabel>Minuman & paparan ulang</SectionLabel><CheckRow label="Ada paparan minuman berpemanis" checked={props.sweetenedBeverageExposure} onChange={props.setSweetenedBeverageExposure} />{props.sweetenedBeverageExposure && <Input label="Hari dengan minuman berpemanis (0–7)" type="number" min="0" max="7" value={props.sweetBeverageDays} onChange={(e) => props.setSweetBeverageDays(e.target.value)} />}<Input label="Hari melakukan paparan ulang makanan (0–7)" type="number" min="0" max="7" value={props.repeatedExposureDays} onChange={(e) => props.setRepeatedExposureDays(e.target.value)} /><CheckRow label="Air putih menjadi minuman utama" checked={props.waterPrimaryBeverage} onChange={props.setWaterPrimaryBeverage} /></>}
    <SectionLabel>Konteks tambahan</SectionLabel>
    <div className="col-span-full"><Input label="Hambatan yang paling terasa" value={props.barriers} onChange={(e) => props.setBarriers(e.target.value)} placeholder="Contoh: bahan sulit tersedia, jadwal keluarga berubah" helperText="Pisahkan dengan koma bila lebih dari satu." /></div>
    <Input label="Alergi makanan yang diketahui" value={props.allergies} onChange={(e) => props.setAllergies(e.target.value)} placeholder="Contoh: telur, susu sapi" />
    <Input label="Pantangan / pola makan" value={props.restrictions} onChange={(e) => props.setRestrictions(e.target.value)} placeholder="Contoh: vegetarian, tidak seafood" />
    <div className="col-span-full"><Textarea label="Konteks medis yang relevan" value={props.medicalContext} onChange={(e) => props.setMedicalContext(e.target.value)} maxLength={200} placeholder="Masukkan hanya konteks yang benar-benar diketahui." helperText="Konteks ini dapat membatasi personalisasi; sistem tidak membuat diagnosis." /></div>
    <div className="col-span-full"><Textarea label="Catatan tambahan" value={props.notes} onChange={(e) => props.setNotes(e.target.value)} maxLength={500} /></div>
  </div></>;
}

function CheckRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return <label className={`group flex min-h-[72px] w-full cursor-pointer self-start items-start gap-3 rounded-xl border px-4 py-4 text-sm font-semibold leading-5 transition-colors focus-within:ring-2 focus-within:ring-primary/20 ${checked ? "border-primary/50 bg-primary-light/45 text-text" : "border-line bg-background text-text hover:border-primary/30 hover:bg-white"}`}><input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="mt-0.5 h-4 w-4 shrink-0 accent-primary" /><span className="min-w-0 flex-1">{label}</span></label>;
}

type ElderlyEatingProps = { appetite: "low" | "typical" | "high"; setAppetite: (value: "low" | "typical" | "high") => void; mealFrequency: string; setMealFrequency: (value: string) => void; activityLevel: "low" | "moderate" | "high"; setActivityLevel: (value: "low" | "moderate" | "high") => void; hydrationPattern: "regular" | "sometimes_low" | "often_low" | "unknown"; setHydrationPattern: (value: ElderlyEatingProps["hydrationPattern"]) => void; eatingIndependence: "independent" | "needs_reminder" | "needs_setup" | "needs_assistance" | "unknown"; setEatingIndependence: (value: ElderlyEatingProps["eatingIndependence"]) => void; caregiverSupport: "none" | "sometimes" | "daily" | "unknown"; setCaregiverSupport: (value: ElderlyEatingProps["caregiverSupport"]) => void; chewingDifficulty: boolean | null; setChewingDifficulty: (value: boolean) => void; swallowingDifficulty: boolean | null; setSwallowingDifficulty: (value: boolean) => void; fieldErrors: FieldErrors };
function ElderlyEatingStep(props: ElderlyEatingProps) {
  return <><StepHeading index="02" title="Kebiasaan Makan Lansia" body="Ceritakan pola makan sehari-hari dan kemampuan makan lansia. Bagian ini terpisah dari penyakit yang sudah diketahui." />
    <div className="space-y-7">
      <div className="grid gap-5 grid-cols-1">
        <Select label="Nafsu makan belakangan ini" value={props.appetite} onChange={(e) => props.setAppetite(e.target.value as ElderlyEatingProps["appetite"])} options={[{ value: "typical", label: "Stabil / seperti biasa" }, { value: "low", label: "Cenderung menurun" }, { value: "high", label: "Cenderung meningkat" }]} />
        <Input label="Frekuensi makan utama per hari" type="number" min="1" max="10" value={props.mealFrequency} onChange={(e) => props.setMealFrequency(e.target.value)} error={props.fieldErrors.mealFrequency || undefined} helperText="Masukkan kebiasaan makan utama sehari-hari, bukan target diet." />
        <Select label="Aktivitas harian" value={props.activityLevel} onChange={(e) => props.setActivityLevel(e.target.value as ElderlyEatingProps["activityLevel"])} options={[{ value: "low", label: "Lebih banyak duduk / istirahat" }, { value: "moderate", label: "Aktif ringan–sedang" }, { value: "high", label: "Aktif bergerak" }]} />
        <Select label="Kebiasaan minum cairan" value={props.hydrationPattern} onChange={(e) => props.setHydrationPattern(e.target.value as ElderlyEatingProps["hydrationPattern"])} options={[{ value: "unknown", label: "Belum yakin" }, { value: "regular", label: "Cukup teratur" }, { value: "sometimes_low", label: "Kadang lebih sedikit" }, { value: "often_low", label: "Sering lebih sedikit" }]} />
        <Select label="Kemandirian saat makan/minum" value={props.eatingIndependence} onChange={(e) => props.setEatingIndependence(e.target.value as ElderlyEatingProps["eatingIndependence"])} options={[{ value: "unknown", label: "Belum ditentukan" }, { value: "independent", label: "Mandiri" }, { value: "needs_reminder", label: "Perlu diingatkan" }, { value: "needs_setup", label: "Perlu disiapkan" }, { value: "needs_assistance", label: "Perlu bantuan langsung" }]} />
        <Select label="Dukungan caregiver" value={props.caregiverSupport} onChange={(e) => props.setCaregiverSupport(e.target.value as ElderlyEatingProps["caregiverSupport"])} options={[{ value: "unknown", label: "Belum ditentukan" }, { value: "none", label: "Tidak ada dukungan rutin" }, { value: "sometimes", label: "Tersedia sesekali" }, { value: "daily", label: "Tersedia setiap hari" }]} />
      </div>
      <section className="border-t border-line pt-5" aria-labelledby="elderly-eating-ability-title">
        <h3 id="elderly-eating-ability-title" className="text-sm font-semibold text-text">Kemampuan makan</h3>
        <p className="mt-1 text-xs leading-5 text-muted">Jawab masing-masing secara eksplisit agar sistem tidak menganggap ada kendala yang sebenarnya tidak dialami.</p>
        <div className="mt-4 grid gap-5 grid-cols-1">
          <div className="rounded-xl border border-line bg-background p-4">
            <p className="text-sm font-semibold text-text">Apakah ada kesulitan mengunyah makanan?</p>
            <div className="mt-3 grid grid-cols-1 gap-2" role="group" aria-label="Kesulitan mengunyah makanan">
              {[{ label: "Tidak ada", value: false }, { label: "Ada", value: true }].map((option) => <button key={option.label} type="button" aria-pressed={props.chewingDifficulty === option.value} onClick={() => props.setChewingDifficulty(option.value)} className={`min-h-11 rounded-lg border px-3 text-sm font-semibold transition ${props.chewingDifficulty === option.value ? "border-primary bg-primary-light/45 text-primary-dark" : "border-line bg-white text-secondary hover:border-primary/40"}`}>{option.label}</button>)}
            </div>
          </div>
          <div className="rounded-xl border border-line bg-background p-4">
            <p className="text-sm font-semibold text-text">Apakah ada kesulitan menelan makanan/minuman?</p>
            <div className="mt-3 grid grid-cols-1 gap-2" role="group" aria-label="Kesulitan menelan makanan atau minuman">
              {[{ label: "Tidak ada", value: false }, { label: "Ada", value: true }].map((option) => <button key={option.label} type="button" aria-pressed={props.swallowingDifficulty === option.value} onClick={() => props.setSwallowingDifficulty(option.value)} className={`min-h-11 rounded-lg border px-3 text-sm font-semibold transition ${props.swallowingDifficulty === option.value ? "border-primary bg-primary-light/45 text-primary-dark" : "border-line bg-white text-secondary hover:border-primary/40"}`}>{option.label}</button>)}
            </div>
            {props.swallowingDifficulty === true ? <p className="mt-3 text-xs leading-5 text-amber-800">Jika benar ada kesulitan menelan, Guided Program otomatis dibatasi karena rekomendasi tekstur/kekentalan membutuhkan penilaian yang lebih aman.</p> : null}
          </div>
        </div>
      </section>
    </div>
  </>;
}

type ElderlyHealthConditionStepProps = {
  hasCondition: boolean | null; setHasCondition: (value: boolean) => void; conditions: ElderlyCondition[]; setConditions: (value: ElderlyCondition[]) => void; otherCondition: string; setOtherCondition: (value: string) => void; validationAttempted: boolean;
};
function ElderlyHealthConditionStep(props: ElderlyHealthConditionStepProps) {
  const toggleCondition = (value: ElderlyCondition) => {
    const next = props.conditions.includes(value) ? props.conditions.filter((item) => item !== value) : [...props.conditions, value];
    props.setConditions(next);
    if (value === "other" && !next.includes("other")) props.setOtherCondition("");
  };
  const conditionError = props.validationAttempted && props.hasCondition === true && props.conditions.length === 0;
  const otherError = props.validationAttempted && props.hasCondition === true && props.conditions.includes("other") && !props.otherCondition.trim();
  return <><StepHeading index="03" title="Kondisi Kesehatan" body="Masukkan hanya penyakit atau kondisi yang memang sudah diketahui atau pernah diberitahukan oleh tenaga kesehatan. SEHATIN menggunakan data ini sebagai konteks edukasi nutrisi, bukan untuk membuat diagnosis." />
    <section aria-labelledby="elderly-condition-question">
      <div className="flex items-start gap-3"><span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-light text-primary-dark"><HeartPulse size={19} /></span><div><h3 id="elderly-condition-question" className="text-lg font-semibold">Apakah lansia memiliki penyakit atau kondisi kesehatan yang sudah diketahui?</h3><p className="mt-1 text-sm leading-6 text-secondary">Jika tidak ada, pilih “Tidak ada” dan lanjutkan. Jika ada, pilih semua kondisi yang sesuai.</p></div></div>
      <div className="mt-5 grid gap-3 grid-cols-1" role="group" aria-label="Apakah lansia memiliki penyakit atau kondisi kesehatan yang sudah diketahui?">
        {[{ value: false, label: "Tidak ada" }, { value: true, label: "Ada" }].map((option) => <button key={option.label} type="button" aria-pressed={props.hasCondition === option.value} onClick={() => props.setHasCondition(option.value)} className={`min-h-14 rounded-xl border px-4 text-left text-sm font-semibold transition ${props.hasCondition === option.value ? "border-primary bg-primary-light/45 text-primary-dark" : "border-line bg-white text-secondary hover:border-primary/40"}`}>{option.label}</button>)}
      </div>
      {props.hasCondition === null && props.validationAttempted ? <p className="mt-2 text-xs font-semibold text-red-700">Pilih “Tidak ada” atau “Ada”.</p> : null}
      {props.hasCondition === true && <div className="mt-6 border-t border-line pt-5"><p className="text-sm font-semibold">Yang mana?</p><p className="mt-1 text-xs leading-5 text-muted">Bisa memilih lebih dari satu kondisi.</p><div className="mt-4 grid gap-3 grid-cols-1">{ELDERLY_CONDITION_OPTIONS.map((option) => <CheckRow key={option.value} label={option.label} checked={props.conditions.includes(option.value)} onChange={() => toggleCondition(option.value)} />)}</div>{conditionError && <p className="mt-2 text-xs font-semibold text-red-700">Pilih minimal satu penyakit atau kondisi kesehatan.</p>}{props.conditions.includes("other") && <div className="mt-4"><Input label="Nama penyakit atau kondisi" value={props.otherCondition} onChange={(e) => props.setOtherCondition(e.target.value)} maxLength={80} placeholder="Contoh: asam urat, osteoporosis, atau kondisi lain" error={otherError ? "Nama kondisi wajib diisi." : undefined} helperText="Teks disimpan sesuai input kamu dan tidak diubah menjadi diagnosis otomatis." /></div>}</div>}
    </section>
  </>;
}

type ElderlyDietaryStepProps = { allergies: string; setAllergies: (value: string) => void; restrictions: string; setRestrictions: (value: string) => void; medicalContext: string; setMedicalContext: (value: string) => void; notes: string; setNotes: (value: string) => void };
function ElderlyDietaryStep(props: ElderlyDietaryStepProps) {
  return <><StepHeading index="04" title="Preferensi & Pantangan" body="Lengkapi alergi, pantangan, atau informasi tambahan yang memengaruhi pilihan makanan. Bagian ini tidak digunakan untuk menebak penyakit." />
    <div className="grid gap-5">
      <Input label="Alergi makanan yang diketahui" value={props.allergies} onChange={(e) => props.setAllergies(e.target.value)} placeholder="Contoh: telur, susu sapi" helperText="Pisahkan dengan koma bila lebih dari satu." />
      <Input label="Pantangan / pola makan" value={props.restrictions} onChange={(e) => props.setRestrictions(e.target.value)} placeholder="Contoh: vegetarian, tidak seafood" helperText="Masukkan pantangan yang memang dijalani." />
      <Textarea label="Konteks kesehatan tambahan (opsional)" value={props.medicalContext} onChange={(e) => props.setMedicalContext(e.target.value)} maxLength={200} placeholder="Contoh: informasi tambahan yang sudah diketahui dan relevan dengan pola makan" helperText="Tidak menggantikan pilihan penyakit pada langkah Kondisi Kesehatan." />
      <Textarea label="Catatan tambahan" value={props.notes} onChange={(e) => props.setNotes(e.target.value)} maxLength={500} placeholder="Contoh: kesulitan menyiapkan makanan atau kebiasaan makan yang ingin diperhatikan" />
    </div>
  </>;
}

type ReviewStepProps = { reviewIndex?: string; stage: NutritionStage; age: string; unit: string; dateOfBirth: string; ageBand: string; sex: string; weight: string; height: string; feedingMode: string; appetite: string; mealFrequency: string; hydrationPattern?: string; eatingIndependence?: string; caregiverSupport?: string; allergies: string; restrictions: string; medicalContext: string; hasCondition: boolean | null; conditions: ElderlyCondition[]; otherCondition: string; validation: NutritionValidation | null };
function ReviewStep({ reviewIndex = "04", stage, age, unit, dateOfBirth, ageBand, sex, weight, height, feedingMode, appetite, mealFrequency, hydrationPattern, eatingIndependence, caregiverSupport, allergies, restrictions, medicalContext, hasCondition, conditions, otherCondition, validation }: ReviewStepProps) {
  const conditionText = stage === "elderly" ? (hasCondition ? conditions.map((item) => elderlyConditionLabel(item, otherCondition)).join(", ") : "Tidak ada yang dilaporkan") : "";
  const rows = [["Kategori", stage === "mpasi" ? "MPASI" : stage === "toddler" ? "Toddler" : "Lansia"], ...(dateOfBirth ? [["Tanggal lahir", dateOfBirth], ["Usia terhitung", `${age} ${unit}`], ["Age band", ageBand]] : [["Usia", `${age} ${unit}`]]), ["Jenis kelamin", sex === "female" ? "Perempuan" : "Laki-laki"], ["Berat", `${weight} kg`], [stage === "elderly" ? "Tinggi" : "Panjang/Tinggi", `${height} cm`], ...(feedingMode ? [["Pola susu", feedingMode]] : []), ["Nafsu makan", appetite], ["Frekuensi makan", `${mealFrequency}×/hari`], ...(stage === "elderly" ? [["Kebiasaan minum", hydrationPattern ?? "unknown"], ["Kemandirian makan", eatingIndependence ?? "unknown"], ["Dukungan caregiver", caregiverSupport ?? "unknown"], ["Kondisi kesehatan", conditionText]] : []), ["Alergi", allergies || "Tidak dicantumkan"], ["Pantangan", restrictions || "Tidak dicantumkan"]];
  return <><StepHeading index={reviewIndex} title="Review before analysis" body="Pastikan informasi benar. Setelah valid, Stage 3 membentuk profile, baseline, primary gap, primary target, dan support targets." /><dl className="divide-y divide-line border-y border-line">{rows.map(([key, value]) => <div key={key} className="grid gap-1 py-4 grid-cols-1"><dt className="text-xs font-bold uppercase tracking-[0.12em] text-muted">{key}</dt><dd className="text-sm font-medium text-text">{value}</dd></div>)}</dl>{validation && <div className="mt-6"><Alert variant={validationVariant(validation.status)} title={`Validasi pengukuran: ${validation.status}`}>{validation.message}</Alert></div>}{medicalContext && <div className="mt-4"><Alert variant="warning" title="Konteks kesehatan terdeteksi">Jika konteks membutuhkan penilaian profesional, sistem dapat membatasi personalisasi demi keamanan.</Alert></div>}<p className="mt-6 text-xs leading-5 text-muted">{stage === "elderly" ? "Hasil digunakan untuk panduan nutrisi edukatif dan tidak merupakan diagnosis medis." : "Gap yang dihasilkan adalah behavioral/nutrition guidance gap, bukan diagnosis atau status kesehatan anak."}</p></>;
}
