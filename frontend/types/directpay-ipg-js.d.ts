declare module "directpay-ipg-js" {
  interface InitConfig {
    signature: string;
    dataString: string;
    stage: string;
    container: string;
  }

  export class Init {
    constructor(config: InitConfig);
    doInAppCheckout(): Promise<unknown>;
  }
}
