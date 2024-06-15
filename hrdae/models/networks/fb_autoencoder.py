from dataclasses import dataclass, field

from torch import Tensor, cat, nn

from .modules import ConvModule1d, ConvModule2d, ConvModule3d


@dataclass
class FiveBranchAutoencoder2dOption:
    in_channels_1d: int = 1
    in_channels_2d: int = 1
    latent_dim: int = 64
    conv_params_1d: list[dict[str, list[int]]] = field(
        default_factory=lambda: [
            {"kernel_size": [3], "stride": [2], "padding": [1], "output_padding": [1]},
        ]
    )
    conv_params_2d: list[dict[str, list[int]]] = field(
        default_factory=lambda: [
            {"kernel_size": [3], "stride": [2], "padding": [1], "output_padding": [1]},
        ]
    )
    weighted: bool = False
    debug_show_dim: bool = False


@dataclass
class FiveBranchAutoencoder3dOption:
    in_channels_2d: int = 1
    in_channels_3d: int = 1
    latent_dim: int = 64
    conv_params_2d: list[dict[str, list[int]]] = field(
        default_factory=lambda: [
            {"kernel_size": [3], "stride": [2], "padding": [1], "output_padding": [1]},
        ]
    )
    conv_params_3d: list[dict[str, list[int]]] = field(
        default_factory=lambda: [
            {"kernel_size": [3], "stride": [2], "padding": [1], "output_padding": [1]},
        ]
    )
    weighted: bool = False
    debug_show_dim: bool = False


def create_fb_autoencoder2d(opt: FiveBranchAutoencoder2dOption) -> nn.Module:
    return FiveBranchAutoencoder2d(
        in_channels_1d=opt.in_channels_1d,
        in_channels_2d=opt.in_channels_2d,
        latent_dim=opt.latent_dim,
        conv_params_1d=opt.conv_params_1d,
        conv_params_2d=opt.conv_params_2d,
        debug_show_dim=opt.debug_show_dim,
    )


def create_fb_autoencoder3d(opt: FiveBranchAutoencoder3dOption) -> nn.Module:
    return FiveBranchAutoencoder3d(
        in_channels_2d=opt.in_channels_2d,
        in_channels_3d=opt.in_channels_3d,
        latent_dim=opt.latent_dim,
        conv_params_2d=opt.conv_params_2d,
        conv_params_3d=opt.conv_params_3d,
        debug_show_dim=opt.debug_show_dim,
    )


class FiveBranchAutoencoder2d(nn.Module):
    def __init__(
        self,
        in_channels_1d: int,
        in_channels_2d: int,
        latent_dim: int,
        conv_params_1d: list[dict[str, list[int]]],
        conv_params_2d: list[dict[str, list[int]]],
        debug_show_dim: bool,
    ) -> None:
        super().__init__()

        self.encoder_1d = ConvModule1d(
            in_channels_1d,
            latent_dim,
            latent_dim,
            conv_params_1d,
            transpose=False,
            debug_show_dim=debug_show_dim,
        )
        self.encoder_2d = ConvModule2d(
            in_channels_2d,
            latent_dim,
            latent_dim,
            conv_params_2d,
            transpose=False,
            debug_show_dim=debug_show_dim,
        )
        self.decoder_2d = ConvModule2d(
            5 * latent_dim,
            in_channels_2d,
            latent_dim,
            conv_params_2d,
            transpose=True,
            debug_show_dim=debug_show_dim,
        )

    def forward(
        self,
        x_1d: Tensor,  # (b, n, s, h)
        x_2d_0: Tensor,  # (b, 2, c, h, w)
        x_1d_0: Tensor,  # (b, 2, s, h)
    ) -> Tensor:
        b, n, s, h = x_1d.size()
        _, _, c, _, w = x_2d_0.size()

        x_1d = x_1d.view(b * n, s, h)
        x_2d_0 = x_2d_0.view(b * 2, c, h, w)
        x_1d_0 = x_1d_0.view(b * 2, s, h)

        # encode
        x_1d = self.encoder_1d(x_1d)
        _, c_, h_ = x_1d.size()
        x_1d = x_1d.view(b * n, 1 * c_, h_, 1)

        x_2d_0 = self.encoder_2d(x_2d_0)
        _, _, _, w_ = x_2d_0.size()
        x_2d_0 = x_2d_0.view(b, 2 * c_, h_, w_)

        x_1d_0 = self.encoder_1d(x_1d_0)
        x_1d_0 = x_1d_0.view(b, 2 * c_, h_, 1)

        # expand
        # (b * n, 1 * c_, h_, 1) -> (b * n, 1 * c_, h_, w_)
        x_1d = x_1d.repeat(1, 1, 1, w_)
        # (b, 2 * c_, h_, w_) -> (b * n, 2 * c_, h_, w_)
        x_2d_0 = x_2d_0.repeat(n, 1, 1, 1)
        # (b, 2 * c_, h_, w_) -> (b * n, 2 * c_, h_, w_)
        x_1d_0 = x_1d_0.repeat(n, 1, 1, w_)

        # aggregate
        latent = cat([x_1d, x_1d_0, x_2d_0], dim=1)

        # decode
        out = self.decoder_2d(latent)
        out = out.view(b, n, c, h, w)
        return out


class FiveBranchAutoencoder3d(nn.Module):
    def __init__(
        self,
        in_channels_2d: int,
        in_channels_3d: int,
        latent_dim: int,
        conv_params_2d: list[dict[str, list[int]]],
        conv_params_3d: list[dict[str, list[int]]],
        debug_show_dim: bool,
    ) -> None:
        super().__init__()

        self.encoder_2d = ConvModule2d(
            in_channels_2d,
            latent_dim,
            latent_dim,
            conv_params_2d,
            transpose=False,
            debug_show_dim=debug_show_dim,
        )
        self.encoder_3d = ConvModule3d(
            in_channels_3d,
            latent_dim,
            latent_dim,
            conv_params_3d,
            transpose=False,
            debug_show_dim=debug_show_dim,
        )
        self.decoder_3d = ConvModule3d(
            5 * latent_dim,
            in_channels_3d,
            latent_dim,
            conv_params_3d,
            transpose=True,
            debug_show_dim=debug_show_dim,
        )

    def forward(
        self,
        x_2d: Tensor,  # (b, n, s, d, h)
        x_3d_0: Tensor,  # (b, 2, c, d, h, w)
        x_2d_0: Tensor,  # (b, 2, s, d, h)
    ) -> Tensor:
        b, n, s, d, h = x_2d.size()
        _, _, c, _, _, w = x_3d_0.size()

        x_2d = x_2d.view(b * n, s, d, h)
        x_3d_0 = x_3d_0.view(b * 2, c, d, h, w)
        x_2d_0 = x_2d_0.view(b * 2, s, d, h)

        # encode
        x_2d = self.encoder_2d(x_2d)
        _, c_, d_, h_ = x_2d.size()
        x_2d = x_2d.view(b * n, 1 * c_, d_, h_, 1)

        x_3d_0 = self.encoder_3d(x_3d_0)
        _, _, _, _, w_ = x_3d_0.size()
        x_3d_0 = x_3d_0.view(b, 2 * c_, d_, h_, w_)

        x_2d_0 = self.encoder_2d(x_2d_0)
        x_2d_0 = x_2d_0.view(b, 2 * c_, d_, h_, 1)

        # expand
        # (b * n, 1 * c_, d_, h_, 1) -> (b * n, 1 * c_, d_, h_, w_)
        x_2d = x_2d.repeat(1, 1, 1, 1, w_)
        # (b, 2 * c_, d_, h_, w_) -> (b * n, 2 * c_, d_, h_, w_)
        x_3d_0 = x_3d_0.repeat(n, 1, 1, 1, 1)
        # (b, 2 * c_, d_, h_, w_) -> (b * n, 2 * c_, d_, h_, w_)
        x_2d_0 = x_2d_0.repeat(n, 1, 1, 1, w_)

        # aggregate
        latent = cat([x_2d, x_2d_0, x_3d_0], dim=1)

        # decode
        out = self.decoder_3d(latent)
        out = out.view(b, n, c, d, h, w)
        return out


if __name__ == "__main__":

    def test():
        from torch import randn

        b, n, c, s, d, h, w = 32, 10, 1, 3, 32, 64, 64

        x_1d = randn(b, n, s, h)
        x_2d_0 = randn(b, 2, c, h, w)
        x_1d_0 = randn(b, 2, s, h)

        model = FiveBranchAutoencoder2d(
            in_channels_1d=s,
            in_channels_2d=1,
            latent_dim=64,
            conv_params_1d=[
                {
                    "kernel_size": [3],
                    "stride": [2],
                    "padding": [1],
                    "output_padding": [1],
                },
                {
                    "kernel_size": [3],
                    "stride": [2],
                    "padding": [1],
                    "output_padding": [1],
                },
            ],
            conv_params_2d=[
                {
                    "kernel_size": [3],
                    "stride": [2],
                    "padding": [1],
                    "output_padding": [1],
                },
                {
                    "kernel_size": [3],
                    "stride": [2],
                    "padding": [1],
                    "output_padding": [1],
                },
            ],
            debug_show_dim=True,
        )
        out = model(x_1d, x_2d_0, x_1d_0)
        print(out.size())

        x_2d = randn(b, n, s, d, h)
        x_3d_0 = randn(b, 2, c, d, h, w)
        x_2d_0 = randn(b, 2, s, d, h)

        model = FiveBranchAutoencoder3d(
            in_channels_2d=s,
            in_channels_3d=1,
            latent_dim=64,
            conv_params_2d=[
                {
                    "kernel_size": [3],
                    "stride": [2],
                    "padding": [1],
                    "output_padding": [1],
                },
                {
                    "kernel_size": [3],
                    "stride": [1, 2],
                    "padding": [1],
                    "output_padding": [0, 1],
                },
            ],
            conv_params_3d=[
                {
                    "kernel_size": [3],
                    "stride": [2],
                    "padding": [1],
                    "output_padding": [1],
                },
                {
                    "kernel_size": [3],
                    "stride": [1, 2, 2],
                    "padding": [1],
                    "output_padding": [0, 1, 1],
                },
            ],
            debug_show_dim=True,
        )
        out = model(x_2d, x_3d_0, x_2d_0)
        print(out.size())

    test()