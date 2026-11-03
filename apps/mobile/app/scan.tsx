import React, { useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRouter } from 'expo-router';
import { QrCode, ShieldCheck } from 'lucide-react-native';
import { Button, Card, Screen, Title } from '../src/components/ui';
import { parseHotelAddress } from '../src/api/hotels';
import { useTheme } from '../src/theme/ThemeProvider';
import { font, space } from '../src/theme/tokens';

/** Scan ONLY hotel HTTPS origins. QR contents never become login credentials or deep links. */
export default function ScanHotel() {
  const router = useRouter();
  const { c } = useTheme();
  const [permission, requestPermission] = useCameraPermissions();
  const [error, setError] = useState('');
  const scanLocked = useRef(false);
  const scan = (data: string) => {
    if (scanLocked.current) return;
    scanLocked.current = true;
    const parsed = parseHotelAddress(data);
    if (!parsed.ok) {
      setError('QR-код должен содержать защищённый HTTPS-адрес гостиницы.');
      scanLocked.current = false;
      return;
    }
    // Require explicit confirmation in Connect. Do not authenticate or navigate to arbitrary URLs.
    router.replace({ pathname: '/connect', params: { hotelAddress: parsed.baseUrl } });
  };
  return (
    <Screen>
      <Title sub="MARINA SMART">Сканирование QR-кода</Title>
      <Card style={{ gap: space.md }}>
        <View style={{ flexDirection: 'row', gap: space.sm, alignItems: 'center' }}>
          <QrCode color={c.primary} size={28} />
          <Text style={[font.body, { color: c.text, flex: 1 }]}>Наведите камеру на QR-код подключения гостиницы.</Text>
        </View>
        {!permission ? <Text style={[font.body, { color: c.textMuted }]}>Проверяем доступ к камере…</Text> :
          !permission.granted ? (
            <Button label="Разрешить доступ к камере" onPress={() => { void requestPermission(); }} />
          ) : (
            <View style={{ height: 320, borderRadius: 20, overflow: 'hidden' }}>
              <CameraView
                style={{ flex: 1 }}
                facing="back"
                barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
                onBarcodeScanned={({ data }) => scan(data)}
              />
            </View>
          )}
        {error ? <Text accessibilityRole="alert" style={[font.small, { color: c.danger }]}>{error}</Text> : null}
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: space.sm }}>
          <ShieldCheck color={c.success} size={20} />
          <Text style={[font.small, { color: c.textMuted, flex: 1 }]}>QR-код передаёт только адрес. Вход выполняется отдельно.</Text>
        </View>
        <Button label="Назад к выбору гостиницы" variant="secondary" onPress={() => router.replace('/connect')} />
      </Card>
    </Screen>
  );
}
