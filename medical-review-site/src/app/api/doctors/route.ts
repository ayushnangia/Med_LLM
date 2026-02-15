import { NextRequest, NextResponse } from 'next/server';
import { getDoctors, registerDoctor } from '@/lib/server-storage';

// GET /api/doctors - List all registered doctors with review counts
export async function GET() {
  try {
    const doctors = await getDoctors();
    return NextResponse.json({ doctors });
  } catch (error) {
    console.error('Error reading doctors:', error);
    return NextResponse.json({ error: 'Failed to read doctors' }, { status: 500 });
  }
}

// POST /api/doctors - Register a new doctor
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name } = body;

    if (!name || typeof name !== 'string' || !name.trim()) {
      return NextResponse.json({ error: 'Missing or invalid name' }, { status: 400 });
    }

    const result = await registerDoctor(name.trim());
    return NextResponse.json({ doctor: result, message: 'Doctor registered successfully' });
  } catch (error) {
    console.error('Error registering doctor:', error);
    return NextResponse.json({ error: 'Failed to register doctor' }, { status: 500 });
  }
}
