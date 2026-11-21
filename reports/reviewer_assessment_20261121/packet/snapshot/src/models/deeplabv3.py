"""EchoNet 风格 DeepLabV3-ResNet50；三通道输入、单前景 logit。"""



def deeplabv3_resnet50():
    """构建 EchoNet 风格的 DeepLabV3-ResNet50 单通道分割模型。"""
    import torch
    import torchvision
    model = torchvision.models.segmentation.deeplabv3_resnet50(
        weights=None, weights_backbone=None, aux_loss=False)
    # 输入为复制后的三通道灰度，输出每像素一个左室前景 logit。
    model.classifier[-1] = torch.nn.Conv2d(model.classifier[-1].in_channels, 1, kernel_size=1)
    return model
