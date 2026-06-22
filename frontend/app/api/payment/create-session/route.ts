import { NextResponse } from "next/server";
import crypto from "crypto";
import { initializeApp, getApps, cert } from "firebase-admin/app";
import { getAuth } from "firebase-admin/auth";
import { getFirestore } from "firebase-admin/firestore";

function getAdminApp() {
  if (getApps().length === 0) {
    const projectId = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
    const clientEmail = process.env.FIREBASE_CLIENT_EMAIL;
    const privateKey = process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, "\n");

    if (clientEmail && privateKey) {
      initializeApp({ credential: cert({ projectId, clientEmail, privateKey }) });
    } else {
      initializeApp({ projectId });
    }
  }
  return getApps()[0];
}

export async function POST(request: Request) {
  try {
    const authHeader = request.headers.get("Authorization");
    if (!authHeader || !authHeader.startsWith("Bearer ")) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    const token = authHeader.slice(7);

    const adminApp = getAdminApp();
    const decoded = await getAuth(adminApp).verifyIdToken(token);
    const uid = decoded.uid;

    const merchantId = process.env.DIRECTPAY_MERCHANT_ID;
    const secret = process.env.DIRECTPAY_SECRET;
    if (!merchantId || !secret) {
      return NextResponse.json({ error: "Payment not configured" }, { status: 500 });
    }

    const displayName = decoded.name || "";
    const nameParts = displayName.split(" ");
    const orderId = `ORDER_${uid}_${Date.now()}`;

    const payload = {
      merchant_id: merchantId,
      amount: "999.00",
      type: "ONE_TIME",
      order_id: orderId,
      currency: "LKR",
      response_url: `${process.env.NEXT_PUBLIC_APP_URL}/api/payment/webhook`,
      return_url: `${process.env.NEXT_PUBLIC_APP_URL}/subscription/success`,
      first_name: nameParts[0] || "",
      last_name: nameParts.slice(1).join(" ") || "",
      email: decoded.email || "",
      phone: "",
      logo: "",
    };

    const dataString = Buffer.from(JSON.stringify(payload)).toString("base64");
    const signature = crypto.createHmac("sha256", secret).update(dataString).digest("hex");

    const db = getFirestore(adminApp);
    await db.collection("orders").doc(orderId).set({
      uid,
      amount: 999.0,
      currency: "LKR",
      status: "pending",
      createdAt: new Date().toISOString(),
    });

    return NextResponse.json({ signature, dataString, orderId });
  } catch (err: unknown) {
    console.error("create-session error:", err);
    const fbErr = err as { code?: string };
    if (fbErr.code?.startsWith("auth/")) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
