import React, { useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRouter } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { QrCode, ShieldCheck } from 'lucide-react-native';
import { Button, Card, Screen, Title } from '../src/components/ui';
import { parseHotelAddress } from '../src/api/hotels';
import { useTheme } from '../src/theme/ThemeProvider';
import { font, space } from '../src/theme/tokens';

/** Scan ONLY hotel HTTPS origins. QR contents never become login credentials or deep links. */
export default function ScanHotel() {
  const router = useRouter();
  const { t } = useTranslation();
  const { c } = useTheme();
  const [permission, requestPermission] = useCameraPermissions();
  const [error, setError] = useState('');
  const scanLocked = useRef(false);
  const scan = (data: string) => {
    if (scanLocked.current) return;
    scanLocked.current = true;
    const parsed = parseHotelAddress(data);
    if (!parsed.ok) {
      setError(t('scan.invalid'));
      scanLocked.current = false;
      return;
    }
    // Require explicit confirmation in Connect. Do not authenticate or navigate to arbitrary URLs.
    router.replace({ pathname: '/connect', params: { hotelAddress: parsed.baseUrl } });
  };
  return (
    <Screen>
      <Title sub="MARINA SMART">{t('scan.title')}</Title>
      <Card style={{ gap: space.md }}>
        <View style={{ flexDirection: 'row', gap: space.sm, alignItems: 'center' }}>
          <QrCode color={c.primary} size={28} />
          <Text style={[font.body, { color: c.text, flex: 1 }]} >{t('scan.instructions')}</Text>
        </View>
        {!permission ? <Text style={[font.body, { color: c.textMuted }]} >{t('scan.checking')}</Text> :
          !permission.granted ? (
            <Button label={t('scan.permission')} onPress={() => { void requestPermission(); }} />
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
          <Text style={[font.small, { color: c.textMuted, flex: 1 }]} >{t('scan.privacy')}</Text>
        </View>
        <Button label={t('scan.back')} variant="secondary" onPress={() => router.replace('/connect')} />
      </Card>
    </Screen>
  );
}
