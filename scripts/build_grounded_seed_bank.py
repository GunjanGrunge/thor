from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "configs"


def add(rows: list[dict], seed_id: str, domain: str, user_query: str, notes: str) -> None:
    rows.append(
        {
            "id": seed_id,
            "domain": domain,
            "user_query": user_query,
            "notes": notes,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(CONFIG_DIR / "grounded_generation_seeds_v4.json"))
    args = parser.parse_args()

    seeds: list[dict] = []

    # Condition-aware combined coaching
    add(seeds, "seed_hypertension_weight_loss_v3", "combined", "I have hypertension and want to lose fat without doing anything unsafe. How should I train and eat?", "Must screen for physician clearance, medications, symptoms, BP control, current activity, and nutrition baseline.")
    add(seeds, "seed_type2_diabetes_beginner_v3", "combined", "I have type 2 diabetes and I am out of shape. What is the safest way to start workouts and improve my diet?", "Must screen for medications, hypoglycemia risk, neuropathy, retinopathy, and current glucose management.")
    add(seeds, "seed_prediabetes_fatigue_v3", "combined", "My labs show prediabetes and I feel tired all the time. What training and food changes should I start with?", "Must avoid crash-diet advice and link movement progression to food quality and meal structure.")
    add(seeds, "seed_pcos_strength_loss_v3", "combined", "I have PCOS and want to lose body fat while getting stronger. What should my training and nutrition look like?", "Must avoid disease-treatment claims and screen for cycle issues, medications, sleep, and current activity.")
    add(seeds, "seed_menopause_recomp_v3", "combined", "I am in menopause and want to improve strength, body composition, and energy. How should I train and eat?", "Must screen for symptoms, lifting history, sleep, recovery, and nutrition context before prescribing details.")
    add(seeds, "seed_ckd_general_fitness_v3", "combined", "I have chronic kidney disease and want to stay active and maintain muscle. How cautious do I need to be with exercise and diet?", "Must be conservative, screen for stage, clinician guidance, symptoms, and avoid generic high-protein advice.")
    add(seeds, "seed_post_cardiac_rehab_transition_v3", "combined", "I finished formal cardiac rehab and want to keep getting fitter on my own. How should I train and eat now?", "Must screen for current symptoms, cardiology guidance, medications, and tolerance.")
    add(seeds, "seed_obesity_joint_pain_v3", "combined", "I am obese, get knee pain with stairs, and want to start losing weight safely. How should I train and eat?", "Must screen for pain severity, joint diagnosis, current mobility, calorie baseline, and realistic adherence.")
    add(seeds, "seed_fatty_liver_lifestyle_v3", "combined", "My doctor told me I have fatty liver and need lifestyle changes. What exercise and nutrition approach makes sense?", "Must stay within lifestyle guidance, screen for medical context, and avoid overclaiming disease reversal.")
    add(seeds, "seed_sleep_apnea_weight_training_v3", "combined", "I have sleep apnea and I am trying to lose weight and get stronger. What should I start with?", "Must screen for CPAP use, daytime fatigue, blood pressure, current activity, and recovery.")

    # Workout-focused
    add(seeds, "seed_beginner_strength_home_v3", "workout", "I am a complete beginner with dumbbells at home. What full-body plan should I start with?", "Must screen for schedule, equipment load, injury history, and tolerance before programming.")
    add(seeds, "seed_low_back_pain_strength_v3", "workout", "I get low back pain when I lift and still want to train for strength and muscle. What should I do?", "Must screen for red flags, triggers, diagnosis, pain severity, and avoid push-through-pain advice.")
    add(seeds, "seed_shoulder_press_pain_v3", "workout", "Overhead pressing and benching make my shoulder hurt. How can I keep training upper body?", "Must screen for pain location, severity, diagnosis, instability symptoms, and movement triggers.")
    add(seeds, "seed_knee_oa_stay_active_v3", "workout", "I have knee osteoarthritis and want to stay active without flaring it up. What training should I do?", "Must use condition-aware exercise logic, ask about symptoms and limits, and avoid unsupported bravado.")
    add(seeds, "seed_older_adult_fall_prevention_v3", "workout", "I am 72 and want to improve balance so I do not fall. What kind of exercise plan should I follow?", "Must screen for fall history, medical issues, walking confidence, and current activity.")
    add(seeds, "seed_postpartum_core_return_v3", "workout", "I am postpartum and unsure when to return to core work and weights. Where should I start?", "Must screen for delivery timing, pelvic floor symptoms, diastasis, red flags, and clinician clearance where relevant.")
    add(seeds, "seed_runner_add_strength_v3", "workout", "I run four times a week and want to add strength work without wrecking recovery. How should I set it up?", "Must screen for mileage, intensity, recovery, lifting experience, and schedule.")
    add(seeds, "seed_hypertrophy_4day_v3", "workout", "I have 4 to 5 years of training experience and want a 4-day hypertrophy split focused on chest and back. Can you outline it?", "Can be more prescriptive, but should still check equipment, recovery, and schedule constraints.")
    add(seeds, "seed_beginner_fat_loss_knee_pain_v3", "workout", "I am a beginner trying to lose fat, but deep squats irritate my knees. How should I train?", "Must ask about pain location, severity, diagnosis, equipment, and current activity.")
    add(seeds, "seed_triathlon_strength_v3", "workout", "I train for triathlon and want gym work that helps performance without trashing my legs. What should I do?", "Must screen for training volume, intensity distribution, race calendar, and fatigue.")

    # Nutrition-focused
    add(seeds, "seed_vegetarian_fat_loss_protein_v3", "nutrition", "I am vegetarian, trying to lose fat, and I train four days a week. How much protein should I eat and what meals make sense?", "Must screen for bodyweight, calorie intake, food preferences, and adherence constraints.")
    add(seeds, "seed_vegan_muscle_gain_v3", "nutrition", "I am vegan and want to gain muscle. How should I set up protein and meals?", "Must screen for bodyweight, calorie status, protein sources, and training age.")
    add(seeds, "seed_teen_football_protein_v3", "nutrition", "My teenage son plays football and wants to gain muscle. How should protein intake be handled?", "Must stay guardian-aware, food-first, and avoid adult-only assumptions.")
    add(seeds, "seed_shift_worker_weight_loss_v3", "nutrition", "I work night shifts and struggle with food timing. How should I eat if I want to lose fat and still train well?", "Must screen for sleep disruption, schedule, hunger patterns, and training timing.")
    add(seeds, "seed_endurance_carbs_v3", "nutrition", "I am training for longer races and keep running out of energy. How should I think about carbs and meal timing?", "Must screen for training volume, duration, GI tolerance, and current fueling habits.")
    add(seeds, "seed_high_bp_diet_v3", "nutrition", "My blood pressure is high and I need to clean up my diet. Where should I start?", "Must screen for current intake, sodium-heavy foods, medications, and practical adherence.")
    add(seeds, "seed_diabetes_meal_structure_v3", "nutrition", "I have type 2 diabetes and need a better meal structure for fat loss and energy. What should I focus on?", "Must screen for medications, glucose issues, current meal pattern, and clinician guidance.")
    add(seeds, "seed_bulking_digestive_issues_v3", "nutrition", "I am trying to gain size but I get bloated eating more food. How should I structure meals?", "Must screen for food tolerances, current calories, fiber load, and meal timing.")
    add(seeds, "seed_menopause_protein_recovery_v3", "nutrition", "I am in menopause and want to eat in a way that supports strength, recovery, and body composition. What should I focus on?", "Must screen for current intake, symptoms, goals, and training frequency.")
    add(seeds, "seed_general_fat_loss_basics_v3", "nutrition", "I am overwhelmed by nutrition advice and just want the basics for losing fat without losing muscle. What should I focus on?", "Must ask bodyweight, activity, current intake, and keep advice practical.")

    # Supplements-focused
    add(seeds, "seed_creatine_healthy_lifter_v3", "supplements", "Should I take creatine if I lift five days a week and want better gym performance?", "Must screen for medical issues, medications, hydration, and training goal. Keep benefit framing balanced.")
    add(seeds, "seed_creatine_ckd_v3", "supplements", "I have chronic kidney disease and was thinking about creatine. Is that safe?", "Must be conservative, ask about stage, physician input, and avoid casual approval.")
    add(seeds, "seed_protein_powder_whole_foods_v3", "supplements", "Do I need protein powder, or can I build muscle with whole food alone?", "Must screen for total intake, convenience, budget, and goal rather than overselling supplements.")
    add(seeds, "seed_caffeine_training_v3", "supplements", "Is caffeine useful before training, and who should be careful with it?", "Must screen for blood pressure, anxiety, sleep issues, timing, and dose sensitivity.")
    add(seeds, "seed_omega3_general_v3", "supplements", "Should I take omega-3 if I train regularly, or is food enough?", "Must keep claims measured and screen for diet pattern, fish intake, and medical context.")
    add(seeds, "seed_multivitamin_overreliance_v3", "supplements", "I train hard and was thinking a multivitamin will cover everything. Is that a good idea?", "Must avoid magical thinking and keep supplements secondary to diet quality.")

    # Sport / population-specific
    add(seeds, "seed_soccer_athlete_recovery_v3", "combined", "I play competitive soccer and want to recover better while staying lean. What should I change in training and nutrition?", "Must screen for schedule, match congestion, body composition goal, and current fueling.")
    add(seeds, "seed_grappling_weight_cut_v3", "combined", "I do grappling and need to drop weight without ruining performance. How should I train and eat?", "Must avoid extreme cutting advice and screen for timeline, current size, hydration, and competition date.")
    add(seeds, "seed_master_lifter_joint_limits_v3", "combined", "I am over 50, still lift seriously, and want to keep progressing without beating up my joints. How should I train and eat?", "Must screen for injuries, recovery, sleep, and current workload.")
    add(seeds, "seed_busy_parent_general_health_v3", "combined", "I am a busy parent with 30 minutes a day. I want better health, strength, and weight control. What should I do?", "Must screen for schedule reality, equipment, fatigue, and eating pattern.")
    add(seeds, "seed_office_worker_deconditioned_v3", "combined", "I sit all day, feel weak, and want to get healthier without going all-in on fitness culture. Where do I start?", "Must screen for medical issues, current activity, preferences, and adherence constraints.")

    # More coverage on women’s health / recovery / pain
    add(seeds, "seed_pelvic_floor_symptoms_training_v3", "workout", "Exercise makes me feel pelvic heaviness and leaking. How should I approach training?", "Must be symptom-aware, ask postpartum history and referral context, and avoid pushing impact work.")
    add(seeds, "seed_chronic_neck_pain_training_v3", "workout", "I work at a desk and get chronic neck pain. I still want to lift. How should I approach training?", "Must screen for red flags, diagnosis, triggers, and avoid random neck exercise prescriptions.")
    add(seeds, "seed_tendinopathy_return_v3", "workout", "I have been told I have tendinopathy and I want to train without making it worse. What should I know?", "Must screen for site, severity, loading tolerance, and current rehab status.")
    add(seeds, "seed_plant_based_endurance_v3", "combined", "I am plant-based and training for endurance events. How should I fuel and strength train without under-recovering?", "Must screen for training volume, current intake, energy availability, and protein sources.")
    add(seeds, "seed_post_illness_return_v3", "workout", "I was sick for a while and feel deconditioned. How do I return to training without overdoing it?", "Must screen for current symptoms, medical guidance, baseline capacity, and return-to-activity tolerance.")

    # Advanced Sports Nutrition (Targeting Textbook & Toolkit)
    add(seeds, "seed_vegan_iron_absorption_v4", "nutrition", "I am a vegan athlete struggling with low energy. How can I maximize iron absorption from my meals?", "Must screen for clinical anemia, complete diet profile, fatigue severity, and recommend Vitamin C pairing while avoiding tea/coffee around meals.")
    add(seeds, "seed_glycogen_sparing_endurance_v4", "nutrition", "I am training for an ultramarathon. How do I structure my fat and carb intake to enhance glycogen sparing?", "Must carefully explain metabolic flexibility, avoid extreme keto claims, and screen for race distance and current fueling strategy.")
    add(seeds, "seed_b6_toxicity_recovery_v4", "supplements", "I take a high-dose B6 supplement for recovery but I read it causes nerve issues. What is the safe upper limit?", "Must heavily emphasize safety, check for paresthesia symptoms, explain water-soluble toxicity, and recommend whole-food sources.")
    add(seeds, "seed_sweat_rate_electrolytes_v4", "nutrition", "I am a heavy sweater when playing soccer in the heat. How do I calculate my sweat rate and sodium replacement?", "Must explain standard sweat testing, avoid generic salt pill advice without context, and screen for cramping or hyponatremia risks.")
    add(seeds, "seed_protein_pacing_recovery_v4", "nutrition", "Does it matter if I eat all my protein in two big meals versus four smaller meals for muscle growth?", "Must cite protein pacing limits per meal, screen for total daily intake, and avoid bro-science.")
    add(seeds, "seed_hydration_osmolality_v4", "nutrition", "Should my sports drink be hypotonic or isotonic for a 2-hour tennis match?", "Explain osmolality, gastric emptying, and screen for individual gut tolerance and environmental heat.")
    add(seeds, "seed_plant_leucine_trigger_v4", "nutrition", "What vegan protein sources actually hit the leucine threshold to trigger muscle protein synthesis?", "Must detail leucine content in soy/pea blends vs isolated sources and screen for total protein goals.")
    add(seeds, "seed_female_triad_reds_v4", "combined", "I am a female runner, losing weight, but my periods stopped and my performance is dropping. What is happening?", "Extremely critical. Must screen for RED-S, advise immediate physician/dietitian consultation, and prioritize adequate fueling over performance gains.")
    add(seeds, "seed_beta_alanine_tingles_v4", "supplements", "I tried beta-alanine and my face went numb. Is this dangerous and how much should I take?", "Check for paresthesia panic, explain harmlessness, advise divided dosing, and confirm the training goal (muscular endurance).")
    add(seeds, "seed_creatine_water_retention_v4", "supplements", "I want to take creatine for sprinting but I am afraid of water weight slowing me down. What is the evidence?", "Must address intracellular vs extracellular retention, and relate it strictly to power-to-weight ratio sports.")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"seeds": seeds}
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output_path), "seed_count": len(seeds)}, indent=2))


if __name__ == "__main__":
    main()
