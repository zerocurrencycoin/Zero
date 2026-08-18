extern crate bellman;
extern crate pairing;
extern crate rand;

use rand::{thread_rng, Rng};

use pairing::{Engine, Field, CurveAffine, CurveProjective, PrimeField};
use pairing::bls12_381::{Bls12, Fr};

use bellman::{Circuit, ConstraintSystem, SynthesisError};
use bellman::groth16::{
    Proof, VerifyingKey, PreparedVerifyingKey,
    generate_random_parameters, prepare_verifying_key,
    create_random_proof, verify_proof,
};

const MIMC_ROUNDS: usize = 322;

fn mimc<E: Engine>(mut xl: E::Fr, mut xr: E::Fr, constants: &[E::Fr]) -> E::Fr {
    assert_eq!(constants.len(), MIMC_ROUNDS);
    for i in 0..MIMC_ROUNDS {
        let mut tmp1 = xl;
        tmp1.add_assign(&constants[i]);
        let mut tmp2 = tmp1;
        tmp2.square();
        tmp2.mul_assign(&tmp1);
        tmp2.add_assign(&xr);
        xr = xl;
        xl = tmp2;
    }
    xl
}

struct MiMCDemo<'a, E: Engine> {
    xl: Option<E::Fr>,
    xr: Option<E::Fr>,
    constants: &'a [E::Fr],
}

impl<'a, E: Engine> Circuit<E> for MiMCDemo<'a, E> {
    fn synthesize<CS: ConstraintSystem<E>>(self, cs: &mut CS) -> Result<(), SynthesisError> {
        assert_eq!(self.constants.len(), MIMC_ROUNDS);
        let mut xl_value = self.xl;
        let mut xl = cs.alloc(|| "preimage xl", || xl_value.ok_or(SynthesisError::AssignmentMissing))?;
        let mut xr_value = self.xr;
        let mut xr = cs.alloc(|| "preimage xr", || xr_value.ok_or(SynthesisError::AssignmentMissing))?;

        for i in 0..MIMC_ROUNDS {
            let cs = &mut cs.namespace(|| format!("round {}", i));
            let mut tmp_value = xl_value.map(|mut e| {
                e.add_assign(&self.constants[i]);
                e.square();
                e
            });
            let mut tmp = cs.alloc(|| "tmp", || tmp_value.ok_or(SynthesisError::AssignmentMissing))?;

            cs.enforce(
                || "tmp = (xL + Ci)^2",
                |lc| lc + xl + (self.constants[i], CS::one()),
                |lc| lc + xl + (self.constants[i], CS::one()),
                |lc| lc + tmp,
            );

            let mut new_xl_value = xl_value.map(|mut e| {
                e.add_assign(&self.constants[i]);
                e.mul_assign(&tmp_value.unwrap());
                e.add_assign(&xr_value.unwrap());
                e
            });

            let mut new_xl = if i == (MIMC_ROUNDS - 1) {
                cs.alloc_input(|| "image", || new_xl_value.ok_or(SynthesisError::AssignmentMissing))?
            } else {
                cs.alloc(|| "new_xl", || new_xl_value.ok_or(SynthesisError::AssignmentMissing))?
            };

            cs.enforce(
                || "new_xL = xR + (xL + Ci)^3",
                |lc| lc + tmp,
                |lc| lc + xl + (self.constants[i], CS::one()),
                |lc| lc + new_xl - xr,
            );

            xr = xl;
            xr_value = xl_value;
            xl = new_xl;
            xl_value = new_xl_value;
        }
        Ok(())
    }
}

/// Hand-ported random-linear-combination batch verifier, using ONLY primitives
/// confirmed present in the pinned pairing::Engine/CurveProjective/CurveAffine
/// traits (pairing 0.14.2, no ff/group split). Ported from zkcrypto/bellman's
/// groth16/src/verifier/batch.rs algorithm, adapted to this crate's API shape
/// (method-based add_assign/mul_assign instead of operator overloading).
fn batch_verify<E: Engine>(
    pvk_raw: &VerifyingKey<E>,
    items: &[(Proof<E>, Vec<E::Fr>)],
    rng: &mut impl Rng,
) -> bool {
    // acc_Gammas[0] corresponds to the implicit a_0 = 1 term (pvk.ic[0]).
    let mut acc_gammas = vec![E::Fr::zero(); pvk_raw.ic.len()];
    let mut acc_delta = <E::G1Affine as CurveAffine>::Projective::zero();
    let mut acc_y = E::Fr::zero();
    let mut ml_terms: Vec<(<E::G1Affine as CurveAffine>::Prepared, <E::G2Affine as CurveAffine>::Prepared)> = vec![];

    for (proof, inputs) in items {
        if inputs.len() + 1 != pvk_raw.ic.len() {
            return false;
        }

        // Random nonzero scalar z_i for this proof.
        let z: E::Fr = loop {
            let z: E::Fr = rng.gen();
            if !z.is_zero() {
                break z;
            }
        };

        // ml_terms += (z * A, -B)
        let za = proof.a.mul(z.into_repr()).into_affine();
        let mut neg_b = proof.b;
        neg_b.negate();
        ml_terms.push((za.prepare(), neg_b.prepare()));

        acc_gammas[0].add_assign(&z);
        for (a_i, acc_gamma_i) in inputs.iter().zip(acc_gammas.iter_mut().skip(1)) {
            let mut term = z;
            term.mul_assign(a_i);
            acc_gamma_i.add_assign(&term);
        }

        let zc = proof.c.mul(z.into_repr());
        acc_delta.add_assign(&zc);
        acc_y.add_assign(&z);
    }

    // ml_terms += (acc_Delta, delta_g2)
    ml_terms.push((acc_delta.into_affine().prepare(), pvk_raw.delta_g2.prepare()));

    // Psi = sum_i acc_Gammas[i] * ic[i]
    let mut psi = <E::G1Affine as CurveAffine>::Projective::zero();
    for (ic_i, acc_gamma_i) in pvk_raw.ic.iter().zip(acc_gammas.iter()) {
        let term = ic_i.mul(acc_gamma_i.into_repr());
        psi.add_assign(&term);
    }
    ml_terms.push((psi.into_affine().prepare(), pvk_raw.gamma_g2.prepare()));

    // ml_terms += (acc_Y * alpha_g1, beta_g2)
    let y_alpha = pvk_raw.alpha_g1.mul(acc_y.into_repr()).into_affine();
    ml_terms.push((y_alpha.prepare(), pvk_raw.beta_g2.prepare()));

    let ml_refs: Vec<(&<E::G1Affine as CurveAffine>::Prepared, &<E::G2Affine as CurveAffine>::Prepared)> =
        ml_terms.iter().map(|(a, b)| (a, b)).collect();

    let result = E::final_exponentiation(&E::miller_loop(ml_refs.iter())).unwrap();
    result == E::Fqk::one()
}

fn make_batch<E: Engine>(
    params_vk: &VerifyingKey<E>,
    circuit_params: &bellman::groth16::Parameters<E>,
    constants: &[E::Fr],
    n: usize,
    corrupt_index: Option<usize>,
    rng: &mut impl Rng,
) -> Vec<(Proof<E>, Vec<E::Fr>)> {
    let mut out = Vec::with_capacity(n);
    for i in 0..n {
        let xl: E::Fr = rng.gen();
        let xr: E::Fr = rng.gen();
        let image = mimc::<E>(xl, xr, constants);

        let c = MiMCDemo::<E> { xl: Some(xl), xr: Some(xr), constants };
        let proof = create_random_proof(c, circuit_params, rng).unwrap();

        let used_image = if Some(i) == corrupt_index {
            // Corrupt: use a wrong public input (image that doesn't match the proof).
            let mut bad = image;
            bad.add_assign(&E::Fr::one());
            bad
        } else {
            image
        };
        out.push((proof, vec![used_image]));
    }
    let _ = params_vk;
    out
}

fn main() {
    let rng = &mut thread_rng();
    let constants: Vec<Fr> = (0..MIMC_ROUNDS).map(|_| rng.gen()).collect();

    println!("[phase1] generating circuit parameters (MiMC/Bls12, {} rounds)...", MIMC_ROUNDS);
    let params = {
        let c = MiMCDemo::<Bls12> { xl: None, xr: None, constants: &constants };
        generate_random_parameters(c, rng).unwrap()
    };
    let pvk: PreparedVerifyingKey<Bls12> = prepare_verifying_key(&params.vk);

    let mut all_pass = true;

    // Test 1: sanity check batch_verify against verify_proof for N=1 all-valid.
    for n in [1usize, 2, 8, 64] {
        let batch = make_batch(&params.vk, &params, &constants, n, None, rng);

        // Reference: verify each individually via the existing verify_proof.
        let reference_ok = batch.iter().all(|(p, inputs)| verify_proof(&pvk, p, inputs).unwrap());

        let batch_ok = batch_verify(&params.vk, &batch, rng);

        let pass = reference_ok == true && batch_ok == true;
        println!(
            "[N={:3}] all-valid: reference_ok={} batch_ok={} => {}",
            n, reference_ok, batch_ok, if pass { "PASS" } else { "FAIL" }
        );
        all_pass &= pass;
    }

    // Test 2: one corrupted proof among N -- batch must reject.
    for n in [2usize, 8, 64] {
        let bad_index = n / 2;
        let batch = make_batch(&params.vk, &params, &constants, n, Some(bad_index), rng);

        let reference_all_ok = batch.iter().all(|(p, inputs)| verify_proof(&pvk, p, inputs).unwrap());
        let batch_ok = batch_verify(&params.vk, &batch, rng);

        // Expect: reference detects the bad proof (not all ok), and batch also rejects.
        let pass = reference_all_ok == false && batch_ok == false;
        println!(
            "[N={:3}] 1-bad-among-N (idx={}): reference_all_ok={} batch_ok={} => {}",
            n, bad_index, reference_all_ok, batch_ok, if pass { "PASS" } else { "FAIL" }
        );
        all_pass &= pass;
    }

    if all_pass {
        println!("\n[phase1] ALL TESTS PASSED");
        std::process::exit(0);
    } else {
        println!("\n[phase1] SOME TESTS FAILED");
        std::process::exit(1);
    }
}
