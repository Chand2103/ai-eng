import { NextResponse } from "next/server";
import crypto from "crypto";
import { initializeApp, getApps, cert } from "firebase-admin/app";
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
    const secret = process.env.DIRECTPAY_SECRET;
    if (!secret) {
      return NextResponse.json({ error: "Not configured" }, { status: 500 });
    }

    const rawBody = await request.text();

    const authHeader = request.headers.get("Authorization");
    if (!authHeader) {
      return NextResponse.json({ error: "Missing signature" }, { status: 400 });
    }
    const parts = authHeader.split(" ");
    const receivedHash = parts[1] || parts[0];

    const expectedHash = crypto.createHmac("sha256", secret).update(rawBody).digest("hex");

    const expectedBuf = Buffer.from(expectedHash, "utf8");
    const receivedBuf = Buffer.from(receivedHash, "utf8");
    if (
      expectedBuf.length !== receivedBuf.length ||
      !crypto.timingSafeEqual(expectedBuf, receivedBuf)
    ) {
      return NextResponse.json({ error: "Invalid signature" }, { status: 400 });
    }

    const body = JSON.parse(rawBody);
    const orderId = body.order_id;
    const statusCode = body.status_code;
    const paymentId = body.payment_id;

    if (!orderId) {
      return NextResponse.json({ error: "Missing order_id" }, { status: 400 });
    }

    const adminApp = getAdminApp();
    const db = getFirestore(adminApp);

    const isSuccess = String(statusCode) === "1" || statusCode === 1;

    if (isSuccess) {
      await db.collection("orders").doc(orderId).update({
        status: "completed",
        paymentId: paymentId || "",
        completedAt: new Date().toISOString(),
      });

      const orderSnap = await db.collection("orders").doc(orderId).get();
      const orderData = orderSnap.data();
      const uid = orderData?.uid as string | undefined;

      if (uid) {
        await db.collection("users").doc(uid).update({
          subscription: {
            active: true,
            plan: "pro",
            startedAt: new Date().toISOString(),
            orderId: orderId,
          },
        });
      }
    } else {
      await db.collection("orders").doc(orderId).update({
        status: "failed",
        paymentId: paymentId || "",
        completedAt: new Date().toISOString(),
      });
    }

    return NextResponse.json({ received: true });
  } catch (err) {
    console.error("webhook error:", err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
