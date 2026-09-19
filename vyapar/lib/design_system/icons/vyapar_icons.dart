import 'package:flutter/material.dart';
import 'package:hugeicons/hugeicons.dart';

abstract final class VyaparIcons {
  static const home = HugeIcons.strokeRoundedHome01;
  static const inventory = HugeIcons.strokeRoundedPackage;
  static const orders = HugeIcons.strokeRoundedShoppingCart01;
  static const munim = HugeIcons.strokeRoundedBot;
  static const mic = HugeIcons.strokeRoundedMic01;
  static const notification = HugeIcons.strokeRoundedNotification02;
  static const profile = HugeIcons.strokeRoundedUser;
  static const settings = HugeIcons.strokeRoundedSettings01;
  static const analytics = HugeIcons.strokeRoundedChart;
  static const success = HugeIcons.strokeRoundedCheckmarkCircle01;
  static const warning = HugeIcons.strokeRoundedAlertCircle;
  static const search = HugeIcons.strokeRoundedSearch01;
  static const back = HugeIcons.strokeRoundedArrowLeft02;
  static const forward = HugeIcons.strokeRoundedArrowRight02;
  static const store = HugeIcons.strokeRoundedStore01;
  static const offline = HugeIcons.strokeRoundedWifiOff01;
  static const refresh = HugeIcons.strokeRoundedRefresh;
  static const logout = HugeIcons.strokeRoundedLogout01;
  static const clock = HugeIcons.strokeRoundedClock01;
  static const delivery = HugeIcons.strokeRoundedTruckDelivery;
  static const language = HugeIcons.strokeRoundedLanguageCircle;
  static const security = HugeIcons.strokeRoundedSecurityCheck;
  static const more = HugeIcons.strokeRoundedMoreHorizontal;
  static const insight = HugeIcons.strokeRoundedSparkles;
  static const edit = HugeIcons.strokeRoundedEdit02;
  static const reject = HugeIcons.strokeRoundedCancelCircle;
  static const inbox = HugeIcons.strokeRoundedInbox;
  static const email = HugeIcons.strokeRoundedMail01;
  static const password = HugeIcons.strokeRoundedLock;
  static const visible = HugeIcons.strokeRoundedView;
  static const hidden = HugeIcons.strokeRoundedViewOff;
  static const info = HugeIcons.strokeRoundedInformationCircle;
  static const telegram = HugeIcons.strokeRoundedTelegram;
  static const whatsapp = HugeIcons.strokeRoundedWhatsapp;
  static const qrCode = HugeIcons.strokeRoundedQrCode01;
  static const wallet = HugeIcons.strokeRoundedWallet02;
  static const chartUp = HugeIcons.strokeRoundedChartUp;
  static const userGroup = HugeIcons.strokeRoundedUserGroup;
  static const truck = HugeIcons.strokeRoundedTruckDelivery;
  static const tag = HugeIcons.strokeRoundedSaleTag01;
  static const invoice = HugeIcons.strokeRoundedInvoice01;
  static const bank = HugeIcons.strokeRoundedBank;
  static const megaphone = HugeIcons.strokeRoundedMegaphone01;
  static const location = HugeIcons.strokeRoundedLocation01;
  static const smartphone = HugeIcons.strokeRoundedSmartPhone01;
  static const car = HugeIcons.strokeRoundedCar01;
  static const bulb = HugeIcons.strokeRoundedBulb;
  static const moneyReceive = HugeIcons.strokeRoundedMoneyReceive01;
  static const coins = HugeIcons.strokeRoundedCoins01;
  static const scan = HugeIcons.strokeRoundedAiScan;
  static const camera = HugeIcons.strokeRoundedCamera01;
  static const imageUpload = HugeIcons.strokeRoundedImageUpload;
  static const add = HugeIcons.strokeRoundedAdd01;
  static const delete = HugeIcons.strokeRoundedDelete02;
}

class VyaparIcon extends StatelessWidget {
  const VyaparIcon(
    this.icon, {
    super.key,
    this.size,
    this.color,
    this.strokeWidth = 1.7,
  });

  final List<List<dynamic>> icon;
  final double? size;
  final Color? color;
  final double strokeWidth;

  @override
  Widget build(BuildContext context) =>
      HugeIcon(icon: icon, size: size, color: color, strokeWidth: strokeWidth);
}
